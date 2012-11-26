"""The stats engine is what collects the accumulated transactions metrics,
details of errors and slow transactions. There is one instance of the stats
engine per application. This will be cleared upon each succesful harvest of
data whereby it is sent to the core application.

"""

from __future__ import with_statement

import base64
import copy
import logging
import operator
import zlib

import newrelic.lib.simplejson as simplejson

from newrelic.core.internal_metrics import (internal_trace, InternalTrace,
        internal_metric)

_logger = logging.getLogger(__name__)

class ApdexStats(list):

    """Bucket for accumulating apdex metrics.

    """

    # Is based on a list of length 6 as all metrics are sent to the core
    # application as that and list as base class means it encodes direct
    # to JSON as we need it. In this case only the first 3 entries are
    # strictly used for the metric. The 4th and 5th entries are set to
    # be the apdex_t value in use at the time.

    def __init__(self, apdex_t=0.0):
        super(ApdexStats, self).__init__([0, 0, 0, apdex_t, apdex_t, 0])

    satisfying = property(operator.itemgetter(0))
    tolerating = property(operator.itemgetter(1))
    frustrating = property(operator.itemgetter(2))

    def merge_stats(self, other):
        """Merge data from another instance of this object."""

        self[0] += other[0]
        self[1] += other[1]
        self[2] += other[2]

        self[3] = ((self[0] or self[1] or self[2]) and
                min(self[3], other[3]) or other[3])
        self[4] = max(self[4], other[3])

    def merge_apdex_metric(self, metric):
        """Merge data from an apdex metric object."""

        self[0] += metric.satisfying
        self[1] += metric.tolerating
        self[2] += metric.frustrating

        self[3] = ((self[0] or self[1] or self[2]) and
                min(self[3], metric.apdex_t) or metric.apdex_t)
        self[4] = max(self[4], metric.apdex_t)

class TimeStats(list):

    """Bucket for accumulating time and value metrics.

    """

    # Is based on a list of length 6 as all metrics are sent to the core
    # application as that and list as base class means it encodes direct
    # to JSON as we need it.

    def __init__(self):
        super(TimeStats, self).__init__([0, 0.0, 0.0, 0.0, 0.0, 0.0])

    call_count = property(operator.itemgetter(0))
    total_call_time = property(operator.itemgetter(1))
    total_exclusive_call_time = property(operator.itemgetter(2))
    min_call_time = property(operator.itemgetter(3))
    max_call_time = property(operator.itemgetter(4))
    sum_of_squares = property(operator.itemgetter(5))

    def merge_stats(self, other):
        """Merge data from another instance of this object."""

        self[1] += other[1]
        self[2] += other[2]
        self[3] = self[0] and min(self[3], other[3]) or other[3]
        self[4] = max(self[4], other[4])
        self[5] += other[5]

        # Must update the call count last as update of the
        # minimum call time is dependent on initial value.

        self[0] += other[0]

    def merge_time_metric(self, metric):
        """Merge data from a time metric object."""

        duration = metric.duration
        exclusive = metric.exclusive

        if exclusive is None:
            exclusive = duration

        self[1] += duration
        self[2] += exclusive
        self[3] = self[0] and min(self[3], duration) or duration
        self[4] = max(self[4], duration)
        self[5] += duration ** 2

        # Must update the call count last as update of the
        # minimum call time is dependent on initial value.

        self[0] += 1

    def merge_value_metric(self, metric):
        """Merge data from a value metric object."""

        duration = metric.value
        exclusive = metric.value

        self[1] += duration
        self[2] += exclusive
        self[3] = self[0] and min(self[3], duration) or duration
        self[4] = max(self[4], duration)
        self[5] += duration ** 2

        # Must update the call count last as update of the
        # minimum call time is dependent on initial value.

        self[0] += 1

class ValueMetrics(object):

    """Table for collection a set of value metrics.

    """

    def __init__(self):
        self.__stats_table = {}

    def record_value_metric(self, metric):
        """Record a single value metric, merging the data with any data
        from prior value metrics with the same name.

        """

        key = (metric.name, '')
        stats = self.__stats_table.get(key)
        if stats is None:
            stats = TimeStats()
            self.__stats_table[key] = stats
        stats.merge_value_metric(metric)

    def metrics(self):
        """Returns an iterator over the set of value metrics. The items
        returned are a tuple consisting of the metric key and accumulated
        stats for that key.

        """

        return self.__stats_table.iteritems()

class SlowSqlStats(list):

    def __init__(self):
        super(SlowSqlStats, self).__init__([0, 0, 0, 0, None])

    call_count = property(operator.itemgetter(0))
    total_call_time = property(operator.itemgetter(1))
    min_call_time = property(operator.itemgetter(2))
    max_call_time = property(operator.itemgetter(3))
    slow_sql_node = property(operator.itemgetter(4))

    def merge_stats(self, other):
        """Merge data from another instance of this object."""

        self[1] += other[1]
        self[2] = self[0] and min(self[2], other[2]) or other[2]
        self[3] = max(self[3], other[3])

        if self[3] == other[3]:
            self[4] = other[4]

        # Must update the call count last as update of the
        # minimum call time is dependent on initial value.

        self[0] += other[0]

    def merge_slow_sql_node(self, node):
        """Merge data from a slow sql node object."""

        duration = node.duration

        self[1] += duration
        self[2] = self[0] and min(self[2], duration) or duration
        self[3] = max(self[3], duration)

        if self[3] == duration:
            self[4] = node

        # Must update the call count last as update of the
        # minimum call time is dependent on initial value.

        self[0] += 1

class StatsEngine(object):

    """The stats engine object holds the accumulated transactions metrics,
    details of errors and slow transactions. There should be one instance
    of the stats engine per application. This will be cleared upon each
    succesful harvest of data whereby it is sent to the core application.
    No data will however be accumulated while there is no associated
    settings object indicating that application has been successfully
    activated and server side settings received.

    All of the accumlated apdex, time and value metrics are mapped to from
    the same stats table. The key is comprised of a tuple (name, scope).
    For an apdex metric the scope is None. Time metrics should always have
    a string as the scope and it can be either empty or not. Value metrics
    technically overlap in same namespace as time metrics as the scope is
    always an empty string. There are however no checks against adding a
    value metric which clashes with an existing time metric or vice versa.
    If that is done then the results will simply be wrong. The name chose
    for a time or value metric should thus be chosen wisely so as not to
    clash.

    Note that there is no locking performed within the stats engine itself.
    It is assumed the holder and user of the instance performs adequate
    external locking to ensure that multiple threads do not try and update
    it at the same time.

    """

    def __init__(self):
        self.__settings = None
        self.__stats_table = {}
        self.__sql_stats_table = {}
        self.__slow_transaction = None
        self.__slow_transaction_map = {}
        self.__slow_transaction_dry_harvests = 0
        self.__transaction_errors = []
        self.__metric_ids = {}
        self.__saved_transactions = []

    @property
    def settings(self):
        return self.__settings

    @property
    def metric_ids(self):
        """Returns a reference to the dictionary containing the mappings
        from metric (name, scope) to the integer identifier supplied
        back from the core application. These integer identifiers are
        used when sending data to the core application to cut down on
        the size of data being sent.

        """

        return self.__metric_ids

    def update_metric_ids(self, metric_ids):
        """Updates the dictionary containing the mappings from metric
        (name, scope) to the integer identifier supplied back from the
        core application. The input should be an iterable returning a
        list of pairs where first is a dictionary with name and scope
        keys with corresponding values. The second should be the integer
        identifier. The dictionary is converted to a (name, scope) tuple
        for use as key into the internal dictionary containing the
        mappings.

        """

        for key, value in metric_ids:
            key = (key['name'], key['scope'])
            self.__metric_ids[key] = value

    def metrics_count(self):
        """Returns a count of the number of unique metrics currently
        recorded for apdex, time and value metrics.

        """

        return len(self.__stats_table)

    def record_apdex_metric(self, metric):
        """Record a single apdex metric, merging the data with any data
        from prior apdex metrics with the same name.

        """

        if not self.__settings:
            return

        # Note that because we are using a scope here of an empty string
        # we can potentially clash with an unscoped metric. Using None,
        # although it may help to keep them separate in the agent will
        # not make a difference to the data collector which treats None
        # as an empty string anyway.

        key = (metric.name, '')
        stats = self.__stats_table.get(key)
        if stats is None:
            stats = ApdexStats(metric.apdex_t)
            self.__stats_table[key] = stats
        stats.merge_apdex_metric(metric)

        return key

    def record_apdex_metrics(self, metrics):
        """Record the apdex metrics supplied by the iterable for a
        single transaction, merging the data with any data from prior
        apdex metrics with the same name.

        """

        if not self.__settings:
            return

        for metric in metrics:
            self.record_apdex_metric(metric)

    def record_time_metric(self, metric):
        """Record a single time metric, merging the data with any data
        from prior time metrics with the same name and scope.

        """

        if not self.__settings:
            return

        # Scope is forced to be empty string if None as
        # scope of None is reserved for apdex metrics.

        key = (metric.name, metric.scope or '')
        stats = self.__stats_table.get(key)
        if stats is None:
            stats = TimeStats()
            self.__stats_table[key] = stats
        stats.merge_time_metric(metric)

        return key

    def record_time_metrics(self, metrics):
        """Record the time metrics supplied by the iterable for a single
        transaction, merging the data with any data from prior time
        metrics with the same name and scope.

        """

        if not self.__settings:
            return

        for metric in metrics:
            self.record_time_metric(metric)

    def record_value_metric(self, metric):
        """Record a single value metric, merging the data with any data
        from prior value metrics with the same name.

        """

        if not self.__settings:
            return

        # Scope is forced to be empty string. This means
        # that it can overlap with a time metric, but no
        # validation is done to avoid clashes and mixing
        # the two types of metrics will simply cause
        # incorrect data.

        key = (metric.name, '')
        stats = self.__stats_table.get(key)
        if stats is None:
            stats = TimeStats()
            self.__stats_table[key] = stats
        stats.merge_value_metric(metric)

        return key

    def record_value_metrics(self, metrics):
        """Record the value metrics supplied by the iterable, merging
        the data with any data from prior value metrics with the same
        name.

        """

        if not self.__settings:
            return

        for metric in metrics:
            self.record_value_metric(metric)

    def record_slow_sql_node(self, node):
        """Record a single sql metric, merging the data with any data
        from prior sql metrics for the same sql key.

        """

        if not self.__settings:
            return

        key = node.identifier
        stats = self.__sql_stats_table.get(key)
        if stats is None:
            # Only record slow SQL if not already over the limit on
            # how many can be collected in the harvest period.

            settings = self.__settings
            maximum = settings.agent_limits.slow_sql_data
            if len(self.__sql_stats_table) < maximum:
                stats = SlowSqlStats()
                self.__sql_stats_table[key] = stats

        if stats:
            stats.merge_slow_sql_node(node)

        return key

    @internal_trace('Supportability/StatsEngine/Calls/record_transaction')
    def record_transaction(self, transaction):
        """Record any apdex and time metrics for the transaction as
        well as any errors which occurred for the transaction. If the
        transaction qualifies to become the slow transaction remember
        it for later.

        """

        if not self.__settings:
            return

        settings = self.__settings

        error_collector = settings.error_collector
        transaction_tracer = settings.transaction_tracer
        slow_sql = settings.slow_sql

        # Record the apdex, value and time metrics generated from the
        # transaction. Whether time metrics are reported as distinct
        # metrics or into a rollup is in part controlled via settings
        # for minimum number of unique metrics to be reported and thence
        # whether over a time threshold calculated as percentage of
        # overall request time, up to a maximum number of unique
        # metrics. This is intended to limit how many metrics are
        # reported for each transaction and try and cutdown on an
        # explosion of unique metric names. The limits and thresholds
        # are applied after the metrics are reverse sorted based on
        # exclusive times for each metric. This ensures that the metrics
        # with greatest exclusive time are retained over those with
        # lesser time. Such metrics get reported into the performance
        # breakdown tab for specific web transactions.

        with InternalTrace(
                'Supportability/TransactionNode/Calls/apdex_metrics'):
            self.record_apdex_metrics(transaction.apdex_metrics(self))

        with InternalTrace(
                'Supportability/TransactionNode/Calls/value_metrics'):
            self.merge_value_metrics(transaction.custom_metrics.metrics())

        with InternalTrace(
                'Supportability/TransactionNode/Calls/time_metrics'):
            self.record_time_metrics(transaction.time_metrics(self))

        # Capture any errors if error collection is enabled.
        # Only retain maximum number allowed per harvest.

        if (error_collector.enabled and settings.collect_errors and
                len(self.__transaction_errors) <
                settings.agent_limits.errors_per_harvest):
            with InternalTrace(
                    'Supportability/TransactionNode/Calls/error_details'):
                self.__transaction_errors.extend(transaction.error_details())

                self.__transaction_errors = self.__transaction_errors[:
                        settings.agent_limits.errors_per_harvest]

        # Capture any sql traces if transaction tracer enabled.

        if slow_sql.enabled and settings.collect_traces:
            with InternalTrace(
                    'Supportability/TransactionNode/Calls/slow_sql_nodes'):
                for node in transaction.slow_sql_nodes(self):
                    self.record_slow_sql_node(node)

        # Remember as slowest transaction if transaction tracer
        # is enabled, it is over the threshold and slower than
        # any existing transaction seen for this period and in
        # the historical snapshot of slow transactions, plus
        # recording of transaction trace for this transaction
        # has not been suppressed.

        if (not transaction.suppress_transaction_trace and
                    transaction_tracer.enabled and settings.collect_traces):

            duration = transaction.duration
            threshold = transaction_tracer.transaction_threshold

            if threshold is None:
                threshold = transaction.apdex_t * 4

            if duration >= threshold:
                slowest = 0
                name = transaction.path

                if self.__slow_transaction:
                    slowest = self.__slow_transaction.duration
                if name in self.__slow_transaction_map:
                    slowest = max(self.__slow_transaction_map[name], slowest)

                if duration > slowest:
                    self.__slow_transaction = transaction
                    self.__slow_transaction_map[name] = duration

                # Add transaction to the saved list, if transaction has
                # a guid and number of saved transactions is less than
                # the limit.

                if transaction.guid:
                    maximum = settings.agent_limits.saved_transactions
                    if len(self.__saved_transactions) < maximum:
                        self.__saved_transactions.append(transaction)

    @internal_trace('Supportability/StatsEngine/Calls/metric_data')
    def metric_data(self, normalizer=None):
        """Returns a list containing the low level metric data for
        sending to the core application pertaining to the reporting
        period. This consists of tuple pairs where first is dictionary
        with name and scope keys with corresponding values, or integer
        identifier if metric had an entry in dictionary mapping metric
        (name, scope) as supplied from core application. The second is
        the list of accumulated metric data, the list always being of
        length 6.

        """

        if not self.__settings:
            return []

        result = []
        normalized_stats = {}

        # Metric Renaming and Re-Aggregation. After applying the metric
        # renaming rules, the metrics are re-aggregated to collapse the
        # metrics with same names after the renaming.

        if self.__settings.debug.log_raw_metric_data:
            _logger.info('Raw metric data for harvest of %r is %r.',
                    self.__settings.app_name,
                    list(self.__stats_table.iteritems()))

        if normalizer is not None:
            for key, value in self.__stats_table.iteritems():
                key = (normalizer(key[0])[0] , key[1])
                stats = normalized_stats.get(key)
                if stats is None:
                    normalized_stats[key] = copy.copy(value)
                else:
                    stats.merge_stats(value)
        else:
            normalized_stats = self.__stats_table

        if self.__settings.debug.log_normalized_metric_data:
            _logger.info('Normalized metric data for harvest of %r is %r.',
                    self.__settings.app_name,
                    list(normalized_stats.iteritems()))

        for key, value in normalized_stats.iteritems():
            if key not in self.__metric_ids:
                key = dict(name=key[0], scope=key[1])
            else:
                key = self.__metric_ids[key]
            result.append((key, value))

        return result

    def metric_data_count(self):
        """Returns a count of the number of unique metrics.

        """

        if not self.__settings:
            return 0

        return len(self.__stats_table)

    @internal_trace('Supportability/StatsEngine/Calls/error_data')
    def error_data(self):
        """Returns a to a list containing any errors collected during
        the reporting period.

        """

        if not self.__settings:
            return []

        return self.__transaction_errors

    @internal_trace('Supportability/StatsEngine/Calls/slow_sql_data')
    def slow_sql_data(self):

        if not self.__settings:
            return []

        if not self.__sql_stats_table:
            return []

        maximum = self.__settings.agent_limits.slow_sql_data

        slow_sql_nodes = list(sorted(self.__sql_stats_table.values(),
                key=lambda x: x.max_call_time))[-maximum:]

        result = []

        for node in slow_sql_nodes:

            params = {}

            if node.slow_sql_node.stack_trace:
                params['backtrace'] = node.slow_sql_node.stack_trace

            explain_plan = node.slow_sql_node.explain_plan

            if explain_plan:
                params['explain_plan'] = explain_plan

            json_data = simplejson.dumps(params, ensure_ascii=True,
                    encoding='Latin-1', namedtuple_as_object=False,
                    default=lambda o: list(iter(o)))

            params_data = base64.standard_b64encode(zlib.compress(json_data))

            data = [node.slow_sql_node.path,
                    node.slow_sql_node.request_uri,
                    node.slow_sql_node.identifier,
                    node.slow_sql_node.formatted,
                    node.slow_sql_node.metric,
                    node.call_count,
                    node.total_call_time * 1000,
                    node.min_call_time * 1000,
                    node.max_call_time * 1000,
                    params_data]

            result.append(data)

        return result

    @internal_trace('Supportability/StatsEngine/Calls/transaction_trace_data')
    def transaction_trace_data(self):
        """Returns a list of slow transaction data collected
        during the reporting period.

        """
        if not self.__settings:
            return []

        if (not self.__slow_transaction) and (not self.__saved_transactions):
            return []

        trace_data = []
        maximum = self.__settings.agent_limits.transaction_traces_nodes
        traces = list(self.__saved_transactions)

        if (self.__slow_transaction is not None and
                self.__slow_transaction not in traces):
            traces.append(self.__slow_transaction)

        for trace in traces:
            transaction_trace = trace.transaction_trace(self, maximum)

            internal_metric('Supportability/StatsEngine/Counts/'
                            'transaction_sample_data',
                            trace.trace_node_count)

            data = [transaction_trace,
                    trace.string_table.values()]

            if self.__settings.debug.log_transaction_trace_payload:
                _logger.debug('Encoding slow transaction data where '
                              'payload=%r.', data)

            with InternalTrace('Supportability/StatsEngine/JSON/Encode/'
                               'transaction_sample_data'):

                json_data = simplejson.dumps(data, ensure_ascii=True,
                        encoding='Latin-1', namedtuple_as_object=False,
                        default=lambda o: list(iter(o)))

            internal_metric('Supportability/StatsEngine/ZLIB/Bytes/'
                            'transaction_sample_data', len(json_data))

            with InternalTrace('Supportability/StatsEngine/ZLIB/Compress/'
                               'transaction_sample_data'):
                zlib_data = zlib.compress(json_data)

            with InternalTrace('Supportability/StatsEngine/BASE64/Encode/'
                               'transaction_sample_data'):
                pack_data = base64.standard_b64encode(zlib_data)

            root = transaction_trace.root
            force_persist = trace.guid is not None

            trace_data.append([root.start_time,
                    root.end_time - root.start_time,
                    trace.path,
                    trace.request_uri,
                    pack_data,
                    trace.guid,
                    None,
                    force_persist])

        return trace_data

    @internal_trace('Supportability/StatsEngine/Calls/slow_transaction_data')
    def slow_transaction_data(self):
        """Returns a list containing any slow transaction data collected
        during the reporting period.

        NOTE Currently only the slowest transaction for the reporting
        period is retained.

        """

        if not self.__settings:
            return []

        if not self.__slow_transaction:
            return []

        maximum = self.__settings.agent_limits.transaction_traces_nodes

        transaction_trace = self.__slow_transaction.transaction_trace(
                self, maximum)

        internal_metric('Supportability/StatsEngine/Counts/'
                'transaction_sample_data',
                self.__slow_transaction.trace_node_count)

        data = [transaction_trace,
                self.__slow_transaction.string_table.values()]

        if self.__settings.debug.log_transaction_trace_payload:
            _logger.debug('Encoding slow transaction data where '
                    'payload=%r.', data)

        with InternalTrace('Supportability/StatsEngine/JSON/Encode/'
                'transaction_sample_data'):

            json_data = simplejson.dumps(data, ensure_ascii=True,
                    encoding='Latin-1', namedtuple_as_object=False,
                    default=lambda o: list(iter(o)))

        internal_metric('Supportability/StatsEngine/ZLIB/Bytes/'
                'transaction_sample_data', len(json_data))

        with InternalTrace('Supportability/StatsEngine/ZLIB/Compress/'
                'transaction_sample_data'):
            zlib_data = zlib.compress(json_data)

        with InternalTrace('Supportability/StatsEngine/BASE64/Encode/'
                'transaction_sample_data'):
            pack_data = base64.standard_b64encode(zlib_data)

        root = transaction_trace.root

        trace_data = [[root.start_time,
                root.end_time - root.start_time,
                self.__slow_transaction.path,
                self.__slow_transaction.request_uri,
                pack_data]]

        return trace_data

    def reset_stats(self, settings):
        """Resets the accumulated statistics back to initial state and
        associates the application settings object with the stats
        engine. This should be called when application is first
        activated and combined application settings incorporating server
        side settings are available. Would also be called on any forced
        restart of agent or a reconnection due to loss of connection.

        """

        self.__settings = settings
        self.__stats_table = {}
        self.__sql_stats_table = {}
        self.__slow_transaction = None
        self.__slow_transaction_map = {}
        self.__transaction_errors = []
        self.__metric_ids = {}
        self.__saved_transactions = []

    def harvest_snapshot(self):
        """Creates a snapshot of the accumulated statistics, error
        details and slow transaction and returns it. This is a shallow
        copy, only copying the top level objects. The originals are then
        reset back to being empty, with the exception of the dictionary
        mapping metric (name, scope) to the integer identifiers received
        from the core application. The latter is retained as should
        carry forward to subsequent runs. This method would be called
        to snapshot the data when doing the harvest.

        """

        stats = copy.copy(self)

        # The slow transaction map is retained but we need to
        # perform some housework on each harvest snapshot. What
        # we do is add the slow transaction to the map of
        # transactions and if we reach the threshold for maximum
        # number we clear the table. Also clear the table if
        # have number of harvests where no slow transaction was
        # collected.

        if self.__settings is None:
            self.__slow_transaction_dry_harvests = 0
            self.__slow_transaction_map = {}

        elif self.__slow_transaction is None:
            self.__slow_transaction_dry_harvests += 1
            agent_limits = self.__settings.agent_limits
            dry_harvests = agent_limits.slow_transaction_dry_harvests
            if self.__slow_transaction_dry_harvests >= dry_harvests:
                self.__slow_transaction_dry_harvests = 0
                self.__slow_transaction_map = {}

        else:
            self.__slow_transaction_dry_harvests = 0
            name = self.__slow_transaction.path
            duration = self.__slow_transaction.duration
            self.__slow_transaction_map[name] = duration

            top_n = self.__settings.transaction_tracer.top_n
            if len(self.__slow_transaction_map) >= top_n:
                self.__slow_transaction_map = {}

        # We also retain the table of metric IDs. This should be
        # okay for continuing connection. If connection is lost
        # then reset_engine() above would be called and it would
        # be all thrown away so no chance of following through
        # with incorrect mappings. Everything else is reset to
        # initial values.

        self.__stats_table = {}
        self.__sql_stats_table = {}
        self.__slow_transaction = None
        self.__transaction_errors = []
        self.__saved_transactions = []

        return stats

    def create_workarea(self):
        """Creates and returns a new empty stats engine object. This would
        be used to distill stats from a single web transaction before then
        merging it back into the parent under a thread lock.

        """

        stats = StatsEngine()

        stats.__settings = self.__settings

        return stats

    def merge_metric_stats(self, snapshot):

        """Merges metric data from a snapshot. This is used when merging
        data from a single transaction into main stats engine. It would
        also be done if the sending of the metric data from the harvest
        failed and wanted to keep accumulating it for subsequent
        harvest.

        """

        if not self.__settings:
            return

        # Merge back data into any new data which has been
        # accumulated.

        for key, other in snapshot.__stats_table.iteritems():
            stats = self.__stats_table.get(key)
            if not stats:
                self.__stats_table[key] = copy.copy(other)
            else:
                stats.merge_stats(other)

    def merge_other_stats(self, snapshot, merge_traces=True,
            merge_errors=True, merge_sql=True):

        """Merges non metric data from a snapshot. This would only be
        used when merging data from a single transaction into main
        stats engine. It is assumed the snapshot has newer data and
        that any existing data takes precedence where what should be
        collected is not otherwised based on time.

        """

        if not self.__settings:
            return

        settings = self.__settings

        # Append snapshot error details at end to maintain time
        # based order and then trim at maximum to be kept.

        if merge_errors:
            maximum = settings.agent_limits.errors_per_harvest
            self.__transaction_errors.extend(snapshot.__transaction_errors)
            self.__transaction_errors = self.__transaction_errors[:maximum]

        # Add sql traces to the set of existing entries. If over
        # the limit of how many to collect, only merge in if already
        # seen the specific SQL.

        if merge_sql:
            maximum = settings.agent_limits.slow_sql_data
            for key, other in snapshot.__sql_stats_table.iteritems():
                stats = self.__sql_stats_table.get(key)
                if not stats:
                    if len(self.__sql_stats_table) < maximum:
                        self.__sql_stats_table[key] = copy.copy(other)
                else:
                    stats.merge_stats(other)

        # Restore original slow transaction if slower than any newer
        # slow transaction. Also append any saved transactions
        # corresponding to browser traces, trimming them at the maximum
        # to be kept.

        if merge_traces:
            transaction = snapshot.__slow_transaction

            if transaction:
                name = transaction.path
                duration = transaction.duration

                slowest = 0
                if self.__slow_transaction:
                    slowest = self.__slow_transaction.duration
                if name in self.__slow_transaction_map:
                    slowest = max(self.__slow_transaction_map[name], slowest)

                if duration > slowest:
                    self.__slow_transaction = transaction
                    self.__slow_transaction_map[name] = duration

            maximum = settings.agent_limits.saved_transactions
            self.__saved_transactions.extend(snapshot.__saved_transactions)
            self.__saved_transactions = self.__saved_transactions[:maximum]

    def merge_value_metrics(self, metrics):
        """Merges in a set of value metrics. The metrics should be
        provide as an iterable where each item is a tuple of the key and
        the accumulated stats for that metric key.

        """

        if not self.__settings:
            return

        for key, other in metrics:
            stats = self.__stats_table.get(key)
            if not stats:
                self.__stats_table[key] = copy.copy(other)
            else:
                stats.merge_stats(other)
