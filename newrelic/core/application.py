"""This module implements data recording and reporting for an application.

"""

from __future__ import with_statement

import logging
import sys
import threading
import time
import os
import traceback

from functools import partial

from newrelic.core.config import global_settings_dump, global_settings
from newrelic.core.data_collector import (create_session, ForceAgentRestart,
        ForceAgentDisconnect, DiscardDataForRequest, RetryDataForRequest)
from newrelic.core.environment import environment_settings
from newrelic.core.metric import ValueMetric
from newrelic.core.rules_engine import RulesEngine
from newrelic.core.samplers import create_samplers
from newrelic.core.stats_engine import StatsEngine, ValueMetrics
from newrelic.core.thread_profiler import ThreadProfiler
from newrelic.core.internal_metrics import (internal_trace, InternalTrace,
        InternalTraceContext, internal_metric)

try:
    from newrelic.core._thread_utilization import ThreadUtilization
except:
    ThreadUtilization = None

_logger = logging.getLogger(__name__)

class ThreadUtilizationSampler(object):

    def __init__(self, utilization_tracker):
        self._utilization_tracker = utilization_tracker
        self._last_timestamp = time.time()
        self._utilization = self._utilization_tracker.utilization_count()

    def value_metrics(self):
        now = time.time()

        # TODO This needs to be pushed down into _thread_utilization.c.
        # In doing that, need to fix up UtilizationClass count so the
        # reset is optional because in this case a read only variant is
        # needed for getting a per request custom metric of the
        # utilization during period of the request.
        #
        # TODO This currently doesn't take into consideration coroutines
        # and instance bust percentage is percentage of a single thread
        # and not of total available coroutines. Not sure whether can
        # generate something meaningful for coroutines. Also doesn't
        # work for asynchronous systems such as Twisted.

        new_utilization = self._utilization_tracker.utilization_count()

        elapsed_time = now - self._last_timestamp

        utilization = new_utilization - self._utilization

        utilization = utilization / elapsed_time

        self._last_timestamp = now
        self._utilization = new_utilization

        total_threads = self._utilization_tracker.total_threads()

        if total_threads:
            # Don't report any metrics if don't detect any threads
            # available and in use for handling web transactions,
            # otherwise we end up report zero metrics for task systems
            # such as Celery which skews the results wrongly.

            yield ValueMetric(name='Instance/Available',
                    value=total_threads)
            yield ValueMetric(name='Instance/Used',
                    value=utilization)

            busy = total_threads and utilization/total_threads or 0.0

            yield ValueMetric(name='Instance/Busy', value=busy)

class Application(object):

    """Class which maintains recorded data for a single application.

    """

    def __init__(self, app_name, linked_applications=[]):
        _logger.debug('Initializing application with name %r and '
                'linked applications of %r.', app_name, linked_applications)

        self._creation_time = time.time()

        self._app_name = app_name
        self._linked_applications = sorted(set(linked_applications))

        self._process_id = None

        self._period_start = 0.0

        self._active_session = None

        self._transaction_count = 0
        self._last_transaction = 0.0

        self._harvest_count = 0

        self._merge_count = 0
        self._discard_count = 0

        self._agent_restart = 0
        self._agent_shutdown = False

        self._connected_event = threading.Event()

        self._stats_lock = threading.Lock()
        self._stats_engine = StatsEngine()

        self._stats_custom_lock = threading.Lock()
        self._stats_custom_engine = StatsEngine()

        # We setup empty rules engines here even though they will be
        # replaced when application first registered. This is done to
        # avoid a race condition in setting it later. Otherwise we have
        # to use unnecessary locking to protect access.

        self._rules_engine = { 'url': RulesEngine([]), 
                'transaction': RulesEngine([]), 'metric': RulesEngine([]) }

        # Initial set of inbuilt data samplers for this application.

        self._samplers = list(create_samplers())

        self._thread_utilization = None

        if ThreadUtilization is not None:
            self._thread_utilization = ThreadUtilization()
            self._samplers.append(ThreadUtilizationSampler(
                    self._thread_utilization))

        # Thread profiler and state of whether active or not.

        self._thread_profiler = None
        self._profiler_started = False
        self._send_profile_data = False

    @property
    def name(self):
        return self._app_name

    @property
    def linked_applications(self):
        return self._linked_applications

    @property
    def configuration(self):
        return self._active_session and self._active_session.configuration

    @property
    def thread_utilization(self):
        return self._thread_utilization

    def dump(self, file):
        """Dumps details about the application to the file object."""

        print >> file, 'Time Created: %s' % (
                time.asctime(time.localtime(self._creation_time)))
        print >> file, 'Linked Applications: %r' % (
                self._linked_applications)
        print >> file, 'Registration PID: %s' % (
                self._process_id)
        print >> file, 'Harvest Count: %d' % (
                self._harvest_count)
        print >> file, 'Agent Restart: %d' % (
                self._agent_restart)
        print >> file, 'Forced Shutdown: %s' % (
                self._agent_shutdown)

        active_session = self._active_session

        if active_session:
            print >> file, 'Collector URL: %s' % (
                    active_session.collector_url)
            print >> file, 'Agent Run ID: %d' % (
                    active_session.agent_run_id)
            print >> file, 'URL Normalization Rules: %r' % (
                    self._rules_engine['url'].rules)
            print >> file, 'Metric Normalization Rules: %r' % (
                    self._rules_engine['metric'].rules)
            print >> file, 'Transaction Normalization Rules: %r' % (
                    self._rules_engine['transaction'].rules)
            print >> file, 'Harvest Period Start: %s' % (
                    time.asctime(time.localtime(self._period_start)))
            print >> file, 'Transaction Count: %d' % (
                    self._transaction_count)
            print >> file, 'Last Transaction: %s' % (
                    time.asctime(time.localtime(self._last_transaction)))
            print >> file, 'Harvest Metrics Count: %d' % (
                    self._stats_engine.metrics_count())
            print >> file, 'Harvest Merge Count: %d' % (
                    self._merge_count)
            print >> file, 'Harvest Discard Count: %d' % (
                    self._discard_count)

    def activate_session(self):
        """Creates a background thread to initiate registration of the
        application with the data collector if no active session already
        exists. If you want to know whether registration was successful
        then use wait_for_session_activation().

        """

        if self._agent_shutdown:
            return

        if self._active_session:
            return

        self._process_id = os.getpid()

        self._connected_event.clear()

        thread = threading.Thread(target=self.connect_to_data_collector,
                name='NR-Activate-Session/%s' % self.name)
        thread.setDaemon(True)
        thread.start()

    def wait_for_session_activation(self, timeout):
        """When called immediately after a request to initiate
        registration of the application with the data collector and
        create an active session, will wait for period specified by the
        timeout to see if registration is successful.

        """

        self._connected_event.wait(timeout)

        if not self._connected_event.isSet():
            _logger.debug('Timeout waiting for New Relic service '
                    'connection with timeout of %s seconds.', timeout)
            return False

        return True

    def connect_to_data_collector(self):
        """Performs the actual registration of the application with the
        data collector if no current active session.

        """

        if self._agent_shutdown:
            return

        if self._active_session:
            return

        # Register the application with the data collector. Any errors
        # that occur will be dealt with by create_session(). The result
        # will either be a session object or None. In the event of a
        # failure to register we will try again, gradually backing off
        # for longer and longer periods as we retry. The retry interval
        # will be capped at 300 seconds.

        retries = [(15, False, False), (15, False, False),
                   (30, False, False), (60, True, False),
                   (120, False, False), (300, False, True),]

        try:
            while not self._active_session:

                self._active_session = create_session(None, self._app_name,
                        self.linked_applications, environment_settings(),
                        global_settings_dump())

                # We were successful, but first need to make sure we do
                # not have any problems with the agent normalization
                # rules provided by the data collector. These could blow
                # up when being compiled if the patterns are broken or
                # use text which conflicts with extensions in Python's
                # regular expression syntax.

                if self._active_session:
                    configuration = self._active_session.configuration

                    try:
                        settings = global_settings()

                        if settings.debug.log_normalization_rules:
                            _logger.info('The URL normalization rules for '
                                    '%r are %r.', self._app_name,
                                     configuration.url_rules)
                            _logger.info('The metric normalization rules '
                                    'for %r are %r.', self._app_name,
                                     configuration.metric_name_rules)
                            _logger.info('The transaction normalization '
                                    'rules for %r are %r.', self._app_name,
                                     configuration.transaction_name_rules)

                        self._rules_engine['url'] = RulesEngine(
                                configuration.url_rules)
                        self._rules_engine['metric'] = RulesEngine(
                                configuration.metric_name_rules)
                        self._rules_engine['transaction'] = RulesEngine(
                                configuration.transaction_name_rules)

                    except:
                        _logger.exception('The agent normalization rules '
                                'received from the data collector could not '
                                'be compiled properly by the agent due to a '
                                'syntactical error or other problem. Please '
                                'report this to New Relic support for '
                                'investigation.')

                        # For good measure, in this situation we explicitly
                        # shutdown the session as then the data collector
                        # will record this. Ignore any error from this. Then
                        # we discard the session so we go into a retry loop
                        # on presumption that issue with the URL rules will
                        # be fixed.

                        try:
                            self._active_session.shutdown_session()
                        except:
                            pass

                        self._active_session = None

                # Were we successful. If not go into the retry loop. Log
                # warnings or errors as per schedule associated with the
                # retry intervals.

                if not self._active_session:
                    if retries:
                        timeout, warning, error = retries.pop(0)

                        if warning:
                            _logger.warning('Registration of the application '
                                    '%r with the data collector failed after '
                                    'multiple attempts. Check the prior log '
                                    'entries and remedy any issue as '
                                    'necessary, or if the problem persists, '
                                    'report this problem to New Relic '
                                    'support for further investigation.',
                                    self._app_name)

                        elif error:
                            _logger.error('Registration of the application '
                                    '%r with the data collector failed after '
                                    'further additional attempts. Please '
                                    'report this problem to New Relic support '
                                    'for further investigation.',
                                    self._app_name)

                    else:
                        timeout = 300

                    _logger.debug('Retrying registration of the application '
                            '%r with the data collector after a further %d '
                            'seconds.', self._app_name, timeout)

                    time.sleep(timeout)

                    continue

                # Ensure we have cleared out any cached data from a
                # prior agent run for this application.

                configuration = self._active_session.configuration

                with self._stats_lock:
                    self._stats_engine.reset_stats(configuration)

                with self._stats_custom_lock:
                    self._stats_custom_engine.reset_stats(configuration)

                # Record an initial start time for the reporting period and
                # clear record of last transaction processed.

                self._period_start = time.time()

                self._transaction_count = 0
                self._last_transaction = 0.0

                # Clear any prior count of harvest merges due to failures.

                self._merge_count = 0

                # Flag that the session activation has completed to
                # anyone who has been waiting through calling the
                # wait_for_session_activation() method.

                self._connected_event.set()

        except:
            # If an exception occurs after agent has been flagged to be
            # shutdown then we ignore the error. This is because all
            # sorts of wierd errors could occur when main thread start
            # destroying objects and this background thread to register
            # the application is still running.

            if not self._agent_shutdown:
                _logger.exception('Unexpected exception when registering '
                        'agent with the data collector. If this problem '
                        'persists, please report this problem to New Relic '
                        'support for further investigation.')

    def validate_process(self):
        """Logs a warning message if called in a process different to
        where the application was registered. Only logs a message the
        first time this is detected for current active session.

        """

        process_id = os.getpid()

        # Detect where potentially trying to record any data in a
        # process different to where the harvest thread was created.
        # Note that this only works for the case where a section had
        # been activated prior to the process being forked.

        if self._process_id and process_id != self._process_id:
            _logger.warning('Attempt to reactivate application or record '
                    'transactions in a process different to where the '
                    'agent was already registered for application %r. No '
                    'data will be reported for this process with pid of '
                    '%d. Registration of the agent for this application '
                    'occurred in process with pid %d. If no data at all '
                    'is being reported for your application, then please '
                    'report this problem to New Relic support for further '
                    'investigation.', self._app_name, process_id,
                    self._process_id)

            settings = global_settings()

            if settings.debug.log_agent_initialization:
                _logger.info('Process validation check was triggered '
                        'from: %r', ''.join(traceback.format_stack()[:-1]))
            else:
                _logger.debug('Process validation check was triggered '
                        'from: %r', ''.join(traceback.format_stack()[:-1]))

            # We now zero out the process ID so we know we have already
            # generated a warning message.

            self._process_id = 0

    def normalize_name(self, name, rule_type):
        """Applies the agent normalization rules of the the specified
        rule type to the supplied name."""

        if not self._active_session:
            return name, False

        try:
            return self._rules_engine[rule_type].normalize(name)

        except:
            # In the event that the rules engine blows up because of a
            # problem in the rules supplied by the data collector, we
            # log the exception and otherwise return the original.
            #
            # NOTE This has the potential to cause metric grouping
            # issues, but we should not be getting broken rules to begin
            # with if they are validated properly when entered or
            # generated. We could perhaps instead flag that the
            # transaction be ignored and thus not reported.

            _logger.exception('The application of the normalization '
                    'rules for %r has failed. This can indicate '
                    'a problem with the agent rules supplied by the '
                    'data collector. Please report this problem to New '
                    'Relic support for further investigation.', name)

            return name, False

    def record_metric(self, name, value):
        """Record a custom metric against the application independent
        of a specific transaction.

        NOTE that this will require locking of the stats engine for
        custom metrics and so under heavy use will have performance
        issues. It is better to record the custom metric against an
        active transaction as they will then be aggregated at the end of
        the transaction when all other metrics are aggregated and so no
        additional locking will be required.

        """

        if not self._active_session:
            return

        with self._stats_custom_lock:
            self._stats_custom_engine.record_value_metric(
                    ValueMetric(name=name, value=value))

    def record_metrics(self, metrics):
        """Record a set of custom metrics against the application
        independent of a specific transaction.

        NOTE that this will require locking of the stats engine for
        custom metrics and so under heavy use will have performance
        issues. It is better to record the custom metric against an
        active transaction as they will then be aggregated at the end of
        the transaction when all other metrics are aggregated and so no
        additional locking will be required.

        """

        if not self._active_session:
            return

        with self._stats_custom_lock:
            for name, value in metrics:
                self._stats_custom_engine.record_value_metric(
                        ValueMetric(name=name, value=value))

    def record_transaction(self, data):
        """Record a single transaction against this application."""

        if not self._active_session:
            return

        if self._stats_engine.settings is None:
            return

        # Do checks to see whether trying to record a transaction in a
        # different process to that the application was activated in.

        self.validate_process()

        internal_metrics = ValueMetrics()

        with InternalTraceContext(internal_metrics):
            try:
                # We accumulate stats into a workarea and only then merge it
                # into the main one under a thread lock. Do this to ensure
                # that the process of generating the metrics into the stats
                # don't unecessarily lock out another thread.

                stats = self._stats_engine.create_workarea()
                stats.record_transaction(data)

            except:
                _logger.exception('The generation of transaction data has '
                        'failed. This would indicate some sort of internal '
                        'implementation issue with the agent. Please report '
                        'this problem to New Relic support for further '
                        'investigation.')

            with self._stats_lock:
                try:
                    self._transaction_count += 1
                    self._last_transaction = data.end_time

                    internal_metric('Supportability/Transaction/Counts/'
                            'metric_data', stats.metric_data_count())

                    self._stats_engine.merge_metric_stats(stats)
                    self._stats_engine.merge_other_stats(stats)

                    # We merge the internal statistics here as well even
                    # though have popped out of the context where we are
                    # recording. This is okay so long as don't record
                    # anything else after this point. If we do then that
                    # data will not be recorded.

                    self._stats_engine.merge_value_metrics(
                            internal_metrics.metrics())

                except:
                    _logger.exception('The merging of transaction data has '
                            'failed. This would indicate some sort of '
                            'internal implementation issue with the agent. '
                            'Please report this problem to New Relic support '
                            'for further investigation.')

    def start_profiler(self, command_id=0, **kwargs):
        """Triggered by the start_profiler agent command to start a
        thread profiling session.

        """

        if not self._active_session.configuration.thread_profiler.enabled:
            _logger.warning('A thread profiling session was requested '
                    'for %r but thread profiling is disabled by the current '
                    'agent configuration. Enable "thread_profiler.enabled" '
                    'in the agent configuration.', self._app_name)
            return {command_id: {'error': 'The profiler service is disabled'}}

        profile_id = kwargs['profile_id'] 
        sample_period = kwargs['sample_period'] 
        duration = kwargs['duration'] 
        profile_agent_code = kwargs['profile_agent_code'] 

        if self._profiler_started:
            _logger.warning('A thread profiling session was requested for '
                    '%r but a thread profiling session is already in '
                    'progress. Ignoring the subsequent request. '
                    'If this keeps occurring on a regular basis, please '
                    'report this problem to New Relic support for further '
                    'investigation.', self._app_name)
            return {command_id: {'error': 'Profiler already running'}}

        if not hasattr(sys, '_current_frames'):
            _logger.warning('A thread profiling session was requested for '
                    '%r but thread profiling is not supported for the '
                    'Python interpreter being used. Contact New Relic '
                    'support for additional information about supported '
                    'platforms for the thread profiling feature.',
                    self._app_name)
            return {command_id: {'error': 'Profiler not supported'}}

        _logger.info('Starting thread profiling session for %r.',
                self._app_name)

        # Note that the thread profiler is bound to the application and
        # there is no restriction in place to ensure that only one is
        # run at a time in a process. Thus technically one could start
        # thread profiling session against multiple applications in same
        # process. The merits of doing this are limited though, as the
        # thread profiler reports on what all threads in the process are
        # doing and not just those handling transactions related to the
        # specific application.

        self._thread_profiler = ThreadProfiler(self._app_name, profile_id,
                sample_period, profile_agent_code)

        # When starting the profiling session, we actually specify the
        # stop time as being duration starting from when this harvest
        # period started. This is an attempt to have the thread
        # profiling session finish in time to have it reported with the
        # harvest period finishing at about the same time, rather than
        # being held over for the next harvest a minute later.

        self._thread_profiler.start_profiling(self._period_start+duration)

        self._profiler_started = True
        self._send_profile_data = True

        return {command_id: {}} 

    def stop_profiler(self, command_id=0, **kwargs):
        """Triggered by the stop_profiler agent command to forcibly stop
        a thread profiling session prior to it having completed normally.

        """

        if not self._profiler_started:
            _logger.warning('A request was received to stop a thread '
                    'profiling session for %r, but a thread profiling '
                    'session is not running. If this keeps occurring on '
                    'a regular basis, please report this problem to New '
                    'Relic support for further investigation.',
                    self._app_name)
            return {command_id: {'error': 'Profiler not running.'}}

        elif kwargs['profile_id'] != self._thread_profiler.profile_id:
            _logger.warning('A request was received to stop a thread '
                    'profiling session for %r, but the ID %r for '
                    'the current thread profiling session does not '
                    'match the provided ID of %r. If this keeps occurring on '
                    'a regular basis, please report this problem to New '
                    'Relic support for further investigation.',
                    self._app_name, self._thread_profiler.profile_id,
                    kwargs['profile_id'])
            return {command_id: {'error': 'Profiler not running.'}}

        _logger.info('Stopping thread profiling session for %r.',
                self._app_name)

        # To ensure that the thread profiling session stops, we wait for
        # its completion. If we don't need to send back the data from
        # the thread profiling session, we discard the thread profiler
        # immediately.

        self._thread_profiler.stop_profiling(wait_for_completion=True)

        self._send_profile_data = kwargs['report_data']

        if not self._send_profile_data:
            self._thread_profiler = None
            self._profiler_started = False

        return {command_id: {}} 

    def harvest(self, shutdown=False):
        """Performs a harvest, reporting aggregated data for the current
        reporting period to the data collector.

        """

        if self._agent_shutdown:
            return

        if not self._active_session:
            _logger.debug('Cannot perform a data harvest for %r as '
                    'there is no active session.', self._app_name)

            return

        internal_metrics = ValueMetrics()

        with InternalTraceContext(internal_metrics):
            with InternalTrace('Supportability/Harvest/Calls/harvest'):

                self._harvest_count += 1

                start = time.time()

                _logger.debug('Commencing data harvest for %r.',
                        self._app_name)

                # Create a snapshot of the transaction stats and
                # application specific custom metrics stats, then merge
                # them together. The originals will be reset at the time
                # this is done so that any new metrics that come in from
                # this point onwards will be accumulated in a fresh
                # bucket.

                transaction_count = self._transaction_count

                with self._stats_lock:
                    self._transaction_count = 0
                    self._last_transaction = 0.0

                    stats = self._stats_engine.harvest_snapshot()

                with self._stats_custom_lock:
                    stats_custom = self._stats_custom_engine.harvest_snapshot()

                stats.merge_metric_stats(stats_custom)

                # Now merge in any metrics from the data samplers
                # associated with this application.
                #
                # NOTE If a data sampler has problems then what data was
                # collected up to that point is retained. The data
                # collector itself is still retained and would be used
                # again on future harvest. If it is a persistent problem
                # with the data sampler the issue would then reoccur
                # with every harvest. If data sampler is a user provided
                # data sampler, then should perhaps deregister it if it
                # keeps having problems.

                for sampler in self._samplers:
                    try:
                        for metric in sampler.value_metrics():
                            stats.record_value_metric(metric)

                    except:
                        _logger.exception('The merging of value metrics from '
                                'a data sampler has failed. If this issue '
                                'persists then please report this problem to '
                                'New Relic support for further investigation.')

                # Add a metric we can use to track how many harvest
                # periods have occurred.

                stats.record_value_metric(ValueMetric(
                        name='Instance/Reporting', value=0))

                # Create our time stamp as to when this reporting period
                # ends and start reporting the data.

                period_end = time.time()

                # If this harvest is being forcibly triggered on process
                # shutdown, there are transactions recorded, and the
                # duration of the harvest period is less than 1 second,
                # then artificially push out the end time of the harvest
                # period. This is done so that the harvest period is not
                # less than 1 second, otherwise the data collector will
                # throw the data away. This is desirable for case where
                # trying to monitor scripts which perform a one off task
                # and then immediately exit. Also useful when running
                # test scripts.

                if shutdown and transaction_count != 0:
                    if period_end - self._period_start < 1.0:
                        _logger.debug('Stretching harvest duration for '
                                'forced harvest on shutdown.')
                        period_end = self._period_start + 1.001

                try:
                    configuration = self._active_session.configuration

                    # Send the transaction and custom metric data.

                    # Create a metric_normalizer based on normalize_name
                    # If metric rename rules are empty, set normalizer
                    # to None and the stats engine will skip steps as
                    # appropriate.

                    if self._rules_engine['metric'].rules:
                        metric_normalizer = partial(self.normalize_name,
                                rule_type='metric')
                    else:
                        metric_normalizer = None

                    # Pass the metric_normalizer to stats.metric_data to
                    # do metric renaming.

                    metric_data = stats.metric_data(metric_normalizer)

                    internal_metric('Supportability/Harvest/Counts/'
                            'metric_data', len(metric_data))

                    metric_ids = self._active_session.send_metric_data(
                      self._period_start, period_end, metric_data)

                    # Successful, so we update the stats engine with the
                    # new metric IDs and reset the reporting period
                    # start time. If an error occurs after this point,
                    # any remaining data for the period being reported
                    # on will be thrown away. We reset the count of
                    # number of merges we have done due to failures as
                    # only really want to count errors in being able to
                    # report the main transaction metrics.

                    self._merge_count = 0
                    self._period_start = period_end
                    self._stats_engine.update_metric_ids(metric_ids)

                    # Send the accumulated error data.

                    if configuration.collect_errors:
                        error_data = stats.error_data()

                        internal_metric('Supportability/Harvest/Counts/'
                                'error_data', len(error_data))

                        if error_data:
                            self._active_session.send_errors(error_data)

                    if configuration.collect_traces:
                        slow_sql_data = stats.slow_sql_data()

                        internal_metric('Supportability/Harvest/Counts/'
                                'sql_trace_data', len(slow_sql_data))

                        if slow_sql_data:
                            self._active_session.send_sql_traces(slow_sql_data)

                        slow_transaction_data = stats.transaction_trace_data()

                        internal_metric('Supportability/Harvest/Counts/'
                                'transaction_sample_data',
                                len(slow_transaction_data))

                        if slow_transaction_data:
                            self._active_session.send_transaction_traces(
                                    slow_transaction_data)

                    # Get agent commands from collector.

                    agent_commands = self._active_session.get_agent_commands()

                    # For each agent command received, call the
                    # appropiate agent command handler. Reply to the
                    # data collector with the acknowledgement of the
                    # agent command.

                    for command in agent_commands:
                        cmd_id = command[0]
                        cmd_name = command[1]['name']
                        cmd_args = command[1]['arguments']

                        # An agent command is mapped to a method of this
                        # class. If we don't know about a specific agent
                        # command we just ignore it.

                        cmd_handler = getattr(self, cmd_name, None)

                        if cmd_handler is None:
                            _logger.debug('Received unknown agent command '
                                    '%r from the data collector for %r.',
                                    cmd_name, self._app_name)
                            continue

                        cmd_res = cmd_handler(cmd_id, **cmd_args)

                        if cmd_res:
                            self._active_session.send_agent_command_results(
                                    cmd_res)

                    # If a profiling session is already running, check
                    # if it is completed and send the accumulated
                    # profile data back to the data collector. Note that
                    # this come after we process the agent commands as
                    # we might receive an agent command to stop the
                    # profiling session, but still send the data back.
                    # Having the sending of the results last ensures we
                    # send back that data from the stopped profiling
                    # session immediately.

                    if self._profiler_started:
                        profile_data = self._thread_profiler.profile_data()

                        if profile_data and self._send_profile_data:
                            _logger.debug('Reporting thread profiling '
                                    'session data for %r.', self._app_name)

                            self._active_session.send_profile_data(profile_data)

                            self._profiler_started = False
                            self._send_profile_data = False

                    # If this is a final forced harvest for the process
                    # then attempt to shutdown the session.
                    #
                    # If a thread profiling session is running, we need
                    # to make sure we stop that from running as well.

                    if shutdown:
                        if self._profiler_started:
                            _logger.info('Aborting thread profiling session '
                                    'for %r.', self._app_name)

                            self._thread_profiler.stop_profiling(
                                    wait_for_completion=False)

                            self._thread_profiler = None
                            self._profiler_started = False
                            self._send_profile_data = False

                        try:
                            self._active_session.shutdown_session()
                        except:
                            pass

                        self._active_session = None

                except ForceAgentRestart:
                    # The data collector has indicated that we need to
                    # perform an internal agent restart. We attempt to
                    # properly shutdown the session and then initiate a
                    # new session.
                    #
                    # If a thread profiling session is running, we need
                    # to make sure we stop that from running as well as
                    # any data will not be able to be reported later if
                    # do reconnect as will be a different agent run.

                    if self._profiler_started:
                        _logger.info('Aborting thread profiling session '
                                'for %r.', self._app_name)

                        self._thread_profiler.stop_profiling(
                                wait_for_completion=False)

                        self._thread_profiler = None
                        self._profiler_started = False
                        self._send_profile_data = False

                    try:
                        self._active_session.shutdown_session()
                    except:
                        pass

                    self._agent_restart += 1
                    self._active_session = None

                    self.activate_session()

                except ForceAgentDisconnect:
                    # The data collector has indicated that we need to
                    # force disconnect and stop reporting. We attempt to
                    # properly shutdown the session, but don't start a
                    # new one and flag ourselves as shutdown. This
                    # notification is presumably sent when a specific
                    # application is behaving so badly that it needs to
                    # be stopped entirely. It would require a complete
                    # process start to be able to attempt to connect
                    # again and if the server side kill switch is still
                    # enabled it would be told to disconnect once more.
                    #
                    # If a thread profiling session is running, we need
                    # to make sure we stop that from running as well as
                    # the agent will no longer be reporting without a
                    # restart of the process so no point.

                    if self._profiler_started:
                        _logger.info('Aborting thread profiling session '
                                'for %r.', self._app_name)

                        self._thread_profiler.stop_profiling(
                                wait_for_completion=False)

                        self._thread_profiler = None
                        self._profiler_started = False
                        self._send_profile_data = False

                    try:
                        self._active_session.shutdown_session()
                    except:
                        pass

                    self._active_session = None

                    self._agent_shutdown = True

                except RetryDataForRequest:
                    # A potentially recoverable error occurred. We merge
                    # the stats back into that for the current period
                    # and abort the current harvest if the problem
                    # occurred when initially reporting the main
                    # transaction metrics. If the problem occurred when
                    # reporting other information then that and any
                    # other non reported information is thrown away.
                    #
                    # In order to prevent memory growth will we only
                    # merge data up to a set maximum number of
                    # successive times. When this occurs we throw away
                    # all the metric data and start over. We also only
                    # merge main metric data and discard errors, slow
                    # SQL and transaction traces from older harvest
                    # period.

                    if self._period_start != period_end:

                        self._merge_count += 1

                        agent_limits = configuration.agent_limits
                        maximum = agent_limits.merge_stats_maximum

                        if self._merge_count <= maximum:
                            self._stats_engine.merge_metric_stats(stats)

                        else:
                            _logger.error('Unable to report main transaction '
                                    'metrics after %r successive attempts. '
                                    'Check the log messages and if necessary '
                                    'please report this problem to New Relic '
                                    'support for further investigation.',
                                    maximum)

                            self._discard_count += self._merge_count

                            self._merge_count = 0

                except DiscardDataForRequest:
                    # An issue must have occurred in reporting the data
                    # but if we retry with same data the same error is
                    # likely to occur again so we just throw any data
                    # not sent away for this reporting period.

                    self._discard_count += 1

                except:
                    # An unexpected error, likely some sort of internal
                    # agent implementation issue.

                    _logger.exception('Unexpected exception when attempting '
                            'to harvest the metric data and send it to the '
                            'data collector. Please report this problem to '
                            'New Relic support for further investigation.')

                duration = time.time() - start

                _logger.debug('Completed harvest for %r in %.2f seconds.',
                        self._app_name, duration)

                # Force close the socket connection which has been
                # created for this harvest if session still exists.
                # New connection will be create automatically on the
                # next harvest.

                if self._active_session:
                    self._active_session.close_connection()

        # Merge back in statistics recorded about the last harvest
        # and communication with the data collector. This will be
        # part of the data for the next harvest period.

        with self._stats_lock:
            self._stats_engine.merge_value_metrics(internal_metrics.metrics())
