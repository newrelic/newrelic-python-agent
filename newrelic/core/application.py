import atexit
import threading
import Queue
import json
import zlib
import base64
import sys
import logging
import time

from newrelic.core.remote import NewRelicService
from newrelic.core.nr_threading import QueueProcessingThread

import newrelic.core.metric
import newrelic.core.stats_engine
import newrelic.core.rules_engine
import newrelic.core.samplers

_logger = logging.getLogger('newrelic.core.application')

class Application(object):
    '''
    classdocs
    '''

    def __init__(self, remote, app_name, linked_applications=[]):
        '''
        Constructor
        '''

        self._app_name = app_name
        self._linked_applications = sorted(set(linked_applications))
        self._app_names = [app_name] + linked_applications

        self._remote = remote
        self._service = NewRelicService(remote, self._app_names)

        self._stats_lock = threading.Lock()
        self._stats_engine = newrelic.core.stats_engine.StatsEngine()
        self._stats_custom_lock = threading.Lock()
        self._stats_custom_engine = newrelic.core.stats_engine.StatsEngine()
        self._rules_engine = None

        # we could pull this queue and its processor up to the agent
        self._work_queue = Queue.Queue(10)
        self._work_thread = QueueProcessingThread(("New Relic Worker Thread (%s)" % str(self._app_names)),self._work_queue)
        self._work_thread.start()
        self._work_queue.put_nowait(self.connect)

        self._samplers = newrelic.core.samplers.create_samplers()

        # Force harvesting of metrics on process shutdown. Required
        # as various Python web application hosting mechanisms can
        # restart processes on regular basis and in worst case with
        # CGI/WSGI process, on every request.

        # TODO Note that need to look at possibilities that forcing
        # harvest will hang and whether some timeout mechanism will
        # be needed, otherwise process shutdown may be delayed.

        atexit.register(self.force_harvest)

    @property
    def name(self):
        return self._app_name

    @property
    def linked_applications(self):
        return self._linked_applications

    def stop(self):
        self._work_thread.stop()

    @property
    def configuration(self):
        return self._service.configuration

    def connect(self):
        try:
            _logger.debug("Connecting to the New Relic service.")
            connected = self._service.connect()
            _logger.debug("Connection status is %s." % connected)
            if connected:
                # TODO Is it right that stats are thrown away all the time.
                # What is meant to happen to stats went core application
                # requested a restart?

                # FIXME Could then stats engine objects simply be replaced.

                with self._stats_lock:
                    self._stats_engine.reset_stats(
                            self._service.configuration)

                with self._stats_custom_lock:
                    self._stats_custom_engine.reset_stats(
                            self._service.configuration)

                self._rules_engine = newrelic.core.rules_engine.RulesEngine(
                        self._service.configuration.url_rules)

                _logger.debug("Connected to the New Relic service.")

            return connected
        except:
            _logger.exception('Failed connection startup.')

    def setup_rules_engine(self, rules):
        ruleset = []
        try:
            for item in rules:
                kwargs = {}
                for name in map(str, item.keys()):
                    kwargs[name] = str(item[name])
                rule = newrelic.core.string_normalization.NormalizationRule(
                        **kwargs)
                ruleset.append(rule)
            self._rules_engine = newrelic.core.string_normalization.Normalizer(*ruleset)
        except:
            _logger.exception('Failed to create url rule.')

    def normalize_name(self, name):
        try:
            if not self._rules_engine:
                return name
            return self._rules_engine.normalize(name)
        except:
            _logger.exception('Name normalization failed.')

    def record_metric(self, name, value):
        try:
            self._stats_custom_lock.acquire()
            self._stats_custom_engine.record_value_metric(
                    newrelic.core.metric.ValueMetric(name=name, value=value))
        finally:
            self._stats_custom_lock.release()

    def record_transaction(self, data):
        try:
            start1 = time.time()

	    # We accumulate stats into a workarea and only then
	    # merge it into the main one under a thread lock. Do
	    # this to ensure that the process of generating the
	    # metrics into the stats don't unecessarily lock out
	    # another thread.

            stats = self._stats_engine.create_workarea()
            stats.record_transaction(data)

            duration1 = time.time() - start1

            self._stats_lock.acquire()
            self._stats_engine.merge_stats(stats)
        except:
            _logger.exception('Recording transaction failed.')
        finally:
            duration2 = time.time() - start1
            self._stats_engine.record_value_metric(
                    newrelic.core.metric.ValueMetric(
                    name='Supportability/Agent/Transaction/BuildTime',
                    value=duration1))
            self._stats_engine.record_value_metric(
                    newrelic.core.metric.ValueMetric(
                    name='Supportability/Agent/Transaction/MergeTime',
                    value=duration2-duration1))
            self._stats_engine.record_value_metric(
                    newrelic.core.metric.ValueMetric(
                    name='Supportability/Agent/Transaction/RecordingTime',
                    value=duration2))
            self._stats_lock.release()

    def force_harvest(self):
        connection = self._remote.create_connection()
        self.harvest(connection)

    def harvest(self,connection):
        _logger.debug("Harvesting.")

        stats = None
        stats_custom = None

        try:
            self._stats_lock.acquire()
            stats = self._stats_engine.create_snapshot()
        except:
            _logger.exception('Failed to create snapshot of stats.')
        finally:
            self._stats_lock.release()

        if stats is None:
            return

        try:
            self._stats_custom_lock.acquire()
            stats_custom = self._stats_custom_engine.create_snapshot()
        except:
            _logger.exception('Failed to create snapshot of custom stats.')
        finally:
            self._stats_custom_lock.release()

        if stats_custom:
            stats.merge_stats(stats_custom)

        for sampler in self._samplers:
            for metric in sampler.value_metrics():
                stats.record_value_metric(metric)

        stats.record_value_metric(newrelic.core.metric.ValueMetric(
                name='Instance/Reporting', value=0))

        success = False

        try:
            if self._service.connected():
                metric_ids = self._service.send_metric_data(
                        connection, stats.metric_data())

                # Say we have succeeded once have sent main metrics.
                # If fails for errors and transaction trace then just
                # discard them and keep going.

                # FIXME Is this behaviour the right one.

                success = True

                self._stats_engine.update_metric_ids(metric_ids)

                if self._service.configuration.collect_errors:
                    transaction_errors = stats.transaction_errors
                    if transaction_errors:
                        self._service.send_error_data(
                                connection, stats.transaction_errors)

                # FIXME This may not be right as we may need to
                # massage the format of the sql data if it needs
                # to be compressed. Also need to find out if
                # returns a table of IDs like metric IDs but for
                # the SQL queries or some other response.

                #sql_traces = stats.sql_traces
                #if sql_traces:
                #    self._service.send_sql_data(
                #            connection, stats.sql_traces)

                # FIXME This needs to be cleaned up. It is just to get
                # it working. What part of code should be responsible
                # for doing compressing and final packaging of message.

                if self._service.configuration.collect_traces:
                    slow_transaction = stats.slow_transaction
                    if stats.slow_transaction:
                        transaction_trace = slow_transaction.transaction_trace(
                                stats)
                        compressed_data = base64.encodestring(
                                zlib.compress(json.dumps(transaction_trace)))
                        trace_data = [[transaction_trace.root.start_time,
                                transaction_trace.root.end_time,
                                stats.slow_transaction.path,
                                stats.slow_transaction.request_uri,
                                compressed_data]]

                        self._service.send_trace_data(connection, trace_data)

        except:
            _logger.exception('Data harvest failed.')

        finally:
            if not success:
                try:
                    self._stats_engine.merge_stats(stats, collect_errors=False)
                except:
                    _logger.exception('Failed to remerge harvest data.')
