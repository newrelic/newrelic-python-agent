from __future__ import with_statement

import threading
import zlib
import base64
import sys
import logging
import time

try:
    import json
except:
    try:
        import simplejson as json
    except:
        import newrelic.lib.simplejson as json

import newrelic.core.remote
import newrelic.core.metric
import newrelic.core.stats_engine
import newrelic.core.rules_engine
import newrelic.core.samplers
import newrelic.core.database_utils
import newrelic.core.string_table

_logger = logging.getLogger('newrelic.core.application')

class Application(object):

    def __init__(self, remote, app_name, linked_applications=[]):
        self._app_name = app_name
        self._linked_applications = sorted(set(linked_applications))
        self._app_names = [app_name] + linked_applications

        self._remote = remote
        self._service = newrelic.core.remote.NewRelicService(
                remote, self._app_names)

        self._stats_lock = threading.Lock()
        self._stats_engine = newrelic.core.stats_engine.StatsEngine()

        self._stats_custom_lock = threading.Lock()
        self._stats_custom_engine = newrelic.core.stats_engine.StatsEngine()

        self._rules_engine = None

        self._samplers = newrelic.core.samplers.create_samplers()

        self._connected_event = threading.Event()

    @property
    def name(self):
        return self._app_name

    @property
    def linked_applications(self):
        return self._linked_applications

    @property
    def configuration(self):
        return self._service.configuration

    def activate_session(self):
        self._connected_event.clear()
        thread = threading.Thread(target=self.connect,
                name='NR-Activate-Session/%s' % self.name)
        thread.setDaemon(True)
        thread.start()

    def wait_for_session_activation(self, timeout):
        self._connected_event.wait(timeout)
        if not self._connected_event.isSet():
            _logger.debug("Timeout out waiting for New Relic service "
                          "connection with timeout of %s seconds." % timeout)

    def connect(self):
        try:
            _logger.debug("Connecting to the New Relic service.")
            connected = self._service.connect()
            _logger.debug("Connection status is %s." % connected)
            if connected:
                # TODO Is it right that stats are thrown away all the time.
                # What is meant to happen to stats when core application
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

                # Don't ever clear this at this point so is really only
                # signalling the first successful connection having been
                # made.

                self._connected_event.set()

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
                return name, False
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

    def record_metrics(self, metrics):
        try:
            self._stats_custom_lock.acquire()
            for name, value in metrics:
                self._stats_custom_engine.record_value_metric(
                        newrelic.core.metric.ValueMetric(name=name,
                        value=value))
        finally:
            self._stats_custom_lock.release()

    def record_transaction(self, data):
        try:
            # We accumulate stats into a workarea and only then
            # merge it into the main one under a thread lock. Do
            # this to ensure that the process of generating the
            # metrics into the stats don't unecessarily lock out
            # another thread.

            stats = self._stats_engine.create_workarea()
            stats.record_transaction(data)
        except:
            _logger.exception('Recording transaction failed.')

        try:
            self._stats_lock.acquire()
            self._stats_engine.merge_stats(stats)
        except:
            _logger.exception('Merging transaction failed.')
        finally:
            self._stats_lock.release()

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

                # FIXME This needs to be cleaned up. It is just to get
                # it working. What part of code should be responsible
                # for doing compressing and final packaging of message.

                slow_sql_nodes = list(sorted(stats.sql_stats_table.values(),
                        key=lambda x: x.max_call_time))[-10:]

                if slow_sql_nodes:
                    slow_sql_data = []

                    for node in slow_sql_nodes:

                        params = {}

                        if node.slow_sql_node.stack_trace:
                            params['backtrace'] = node.slow_sql_node.stack_trace 
                        if node.slow_sql_node.explain_plan:
                            params['explain_plan'] = node.slow_sql_node.explain_plan 
                        params_data = base64.standard_b64encode(
                                zlib.compress(json.dumps(params)))

                        data = [node.slow_sql_node.path,
                                node.slow_sql_node.request_uri,
                                hash(node.slow_sql_node.sql_id),
                                node.slow_sql_node.formatted_sql,
                                node.slow_sql_node.metric,
                                node.call_count,
                                node.total_call_time*1000,
                                node.min_call_time*1000,
                                node.max_call_time*1000,
                                params_data]

                        slow_sql_data.append(data)

                    self._service.send_sql_data(
                            connection, slow_sql_data)

                # FIXME This needs to be cleaned up. It is just to get
                # it working. What part of code should be responsible
                # for doing compressing and final packaging of message.

                if self._service.configuration.collect_traces:
                    slow_transaction = stats.slow_transaction
                    if stats.slow_transaction:
                        string_table = newrelic.core.string_table.StringTable()
                        transaction_trace = slow_transaction.transaction_trace(
                                stats, string_table)
                        data = [transaction_trace, string_table.values()]
                        compressed_data = base64.standard_b64encode(
                                zlib.compress(json.dumps(data)))
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

                if not self._service.connected():
                    self.activate_session()

            _logger.debug("Done harvesting.")
