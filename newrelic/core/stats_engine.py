"""The stats engine is what collects the accumulated transactions metrics,
details of errors and slow transactions. There is one instance of the stats
engine per application. This will be cleared upon each succesful harvest of
data whereby it is sent to the core application.

"""

import base64
import copy
import logging
import operator
import random
import zlib
import json

import newrelic.packages.six as six

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

    def __init__(self, satisfying=0, tolerating=0, frustrating=0, apdex_t=0.0):
        super(ApdexStats, self).__init__([satisfying, tolerating,
                frustrating, apdex_t, apdex_t, 0])

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

    def __init__(self, call_count=0, total_call_time=0.0,
                total_exclusive_call_time=0.0, min_call_time=0.0,
                max_call_time=0.0, sum_of_squares=0.0):
        super(TimeStats, self).__init__([call_count, total_call_time,
                total_exclusive_call_time, min_call_time,
                max_call_time, sum_of_squares])

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

    def merge_raw_time_metric(self, duration, exclusive=None):
        """Merge time value."""

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

    def merge_time_metric(self, metric):
        """Merge data from a time metric object."""

        self.merge_raw_time_metric(metric.duration, metric.exclusive)

    def merge_custom_metric(self, value):
        """Merge data value."""

        self.merge_raw_time_metric(value)

class CustomMetrics(object):

    """Table for collection a set of value metrics.

    """

    def __init__(self):
        self.__stats_table = {}

    def __contains__(self, key):
        return key in self.__stats_table

    def record_custom_metric(self, name, value):
        """Record a single value metric, merging the data with any data
        from prior value metrics with the same name.

        """

        stats = self.__stats_table.get(name)
        if stats is None:
            stats = TimeStats()
            self.__stats_table[name] = stats

        def c2t(count=0, total=0.0, min=0.0, max=0.0, sum_of_squares=0.0):
            return (count, total, total, min, max, sum_of_squares)

        try:
            stats.merge_stats(TimeStats(*c2t(**value)))
        except Exception:
            stats.merge_custom_metric(value)

    def metrics(self):
        """Returns an iterator over the set of value metrics. The items
        returned are a tuple consisting of the metric name and accumulated
        stats for the metric.

        """

        return six.iteritems(self.__stats_table)

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

class SampledDataSet(object):

    def __init__(self, capacity=100):
        self.samples = []
        self.capacity = capacity
        self.count = 0
        self.strings = {}

    def reset(self):
        self.samples = []
        self.count = 0
        self.strings = {}

    def add(self, sample):
        if len(self.samples) < self.capacity:
            self.samples.append(sample)
        else:
            index = random.randint(0, self.count)
            if index < self.capacity:
                self.samples[index] = sample
        self.count += 1

    def intern(self, string):
        return self.strings.setdefault(string, string)

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
        self.__sampled_data_set = SampledDataSet()
        self.__sql_stats_table = {}
        self.__slow_transaction = None
        self.__slow_transaction_map = {}
        self.__slow_transaction_old_duration = None
        self.__slow_transaction_dry_harvests = 0
        self.__transaction_errors = []
        self.__metric_ids = {}
        self.__browser_transactions = []
        self.__xray_transactions = []
        self.xray_sessions = {}

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

    @property
    def sampled_data_set(self):
        return self.__sampled_data_set

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
            stats = ApdexStats(apdex_t=metric.apdex_t)
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

    def record_custom_metric(self, name, value):
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

        key = (name, '')
        stats = self.__stats_table.get(key)
        if stats is None:
            stats = TimeStats()
            self.__stats_table[key] = stats

        def c2t(count=0, total=0.0, min=0.0, max=0.0, sum_of_squares=0.0):
            return (count, total, total, min, max, sum_of_squares)

        try:
            stats.merge_stats(TimeStats(*c2t(**value)))
        except Exception:
            stats.merge_custom_metric(value)

        return key

    def record_custom_metrics(self, metrics):
        """Record the value metrics supplied by the iterable, merging
        the data with any data from prior value metrics with the same
        name.

        """

        if not self.__settings:
            return

        for name, value in metrics:
            self.record_custom_metric(name, value)

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

    def _update_xray_transaction(self, transaction):
        """Check if transaction is an xray transaction and save it to the
        __xray_transactions
        """

        settings = self.__settings

        # Nothing to do if we have reached the max limit of xray transactions
        # to send per harvest.

        maximum = settings.agent_limits.xray_transactions
        if len(self.__xray_transactions) >= maximum:
            return

        # If current transaction qualifies as an xray_transaction, set the
        # xray_id on the transaction object and save it in the
        # xray_transactions list.

        xray_session = self.xray_sessions.get(transaction.path)
        if xray_session:
            transaction.xray_id = xray_session.xray_id
            self.__xray_transactions.append(transaction)

    def _update_slow_transaction(self, transaction):
        """Check if transaction is the slowest transaction and update
        accordingly.
        """

        slowest = 0
        name = transaction.path

        if self.__slow_transaction:
            slowest = self.__slow_transaction.duration
        if name in self.__slow_transaction_map:
            slowest = max(self.__slow_transaction_map[name], slowest)

        if transaction.duration > slowest:
            # We are going to replace the prior slow transaction.
            # We need to be a bit tricky here. If we are overriding
            # an existing slow transaction for a different name,
            # then we need to restore in the transaction map what
            # the previous slowest duration was for that, or remove
            # it if there wasn't one. This is so we do not incorrectly
            # suppress it given that it was never actually reported
            # as the slowest transaction.

            if self.__slow_transaction:
                if self.__slow_transaction.path != name:
                    if self.__slow_transaction_old_duration:
                        self.__slow_transaction_map[
                                self.__slow_transaction.path] = (
                                self.__slow_transaction_old_duration)
                    else:
                        del self.__slow_transaction_map[
                                self.__slow_transaction.path]

            if name in self.__slow_transaction_map:
                self.__slow_transaction_old_duration = (
                        self.__slow_transaction_map[name])
            else:
                self.__slow_transaction_old_duration = None

            self.__slow_transaction = transaction
            self.__slow_transaction_map[name] = transaction.duration

    def _update_browser_transaction(self, transaction):
        """Check if transaction is a browser trace and save it to the
        __browser_transaction
        """

        settings = self.__settings

        if not transaction.rum_trace:
            return

        # Check if we have enough browser transactions before adding the
        # current transaction to the list.

        maximum = settings.agent_limits.browser_transactions
        if len(self.__browser_transactions) < maximum:
            self.__browser_transactions.append(transaction)

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
            self.merge_custom_metrics(transaction.custom_metrics.metrics())

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

            # Transactions saved for xray session do not depend on the
            # transaction threshold.

            self._update_xray_transaction(transaction)

            threshold = transaction_tracer.transaction_threshold

            if threshold is None:
                threshold = transaction.apdex_t * 4

            if transaction.duration >= threshold:
                self._update_slow_transaction(transaction)
                self._update_browser_transaction(transaction)

        # Create the transaction record summarising key data for later
        # analytics. Only do this for web transaction at this point as
        # not sure if needs to be done for other transactions as field
        # names in record are based on web transaction metric names.

        if (settings.collect_analytics_events and
                settings.analytics_events.enabled):
            
            if (transaction.type == 'WebTransaction' and
                    settings.analytics_events.transactions.enabled):

                record = {}

                name = self.__sampled_data_set.intern(transaction.path)

                record['type'] = 'Transaction'
                record['name'] = name
                record['timestamp'] = transaction.start_time
                record['duration'] = transaction.duration

                def _update_entry(source, target):
                    try:
                        record[target] = self.__stats_table[
                                (source, '')].total_call_time
                    except KeyError:
                        pass

                _update_entry('HttpDispatcher', 'webDuration')
                _update_entry('WebFrontend/QueueTime', 'queueDuration')

                _update_entry('External/all', 'externalDuration')
                _update_entry('Database/all', 'databaseDuration')
                _update_entry('Memcache/all', 'memcacheDuration')

                self.__sampled_data_set.add([record])

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
                    list(six.iteritems(self.__stats_table)))

        if normalizer is not None:
            for key, value in six.iteritems(self.__stats_table):
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
                    list(six.iteritems(normalized_stats)))

        for key, value in six.iteritems(normalized_stats):
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

        slow_sql_nodes = sorted(six.itervalues(self.__sql_stats_table),
                key=lambda x: x.max_call_time)[-maximum:]

        result = []

        for node in slow_sql_nodes:

            params = {}

            if node.slow_sql_node.stack_trace:
                params['backtrace'] = node.slow_sql_node.stack_trace

            explain_plan = node.slow_sql_node.explain_plan

            if explain_plan:
                params['explain_plan'] = explain_plan

            json_data = json.dumps(params, default=lambda o: list(iter(o)))

            params_data = base64.standard_b64encode(
                    zlib.compress(six.b(json_data)))

            if six.PY3:
                params_data = params_data.decode('Latin-1')

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

        # Create a set 'traces' that is a union of slow transaction,
        # browser_transactions and xray_transactions. This ensures we don't
        # send duplicates of a transaction.

        traces = set()
        if self.__slow_transaction:
            traces.add(self.__slow_transaction)
        traces.update(self.__browser_transactions)
        traces.update(self.__xray_transactions)

        # Return an empty list if no transactions were captured.

        if not traces:
            return []

        trace_data = []
        maximum = self.__settings.agent_limits.transaction_traces_nodes

        for trace in traces:
            transaction_trace = trace.transaction_trace(self, maximum)

            internal_metric('Supportability/StatsEngine/Counts/'
                            'transaction_sample_data',
                            trace.trace_node_count)

            data = [transaction_trace,
                    list(trace.string_table.values())]

            if self.__settings.debug.log_transaction_trace_payload:
                _logger.debug('Encoding slow transaction data where '
                              'payload=%r.', data)

            with InternalTrace('Supportability/StatsEngine/JSON/Encode/'
                               'transaction_sample_data'):

                json_data = json.dumps(data, default=lambda o: list(iter(o)))

            internal_metric('Supportability/StatsEngine/ZLIB/Bytes/'
                            'transaction_sample_data', len(json_data))

            with InternalTrace('Supportability/StatsEngine/ZLIB/Compress/'
                               'transaction_sample_data'):
                zlib_data = zlib.compress(six.b(json_data))

            with InternalTrace('Supportability/StatsEngine/BASE64/Encode/'
                               'transaction_sample_data'):
                pack_data = base64.standard_b64encode(zlib_data)

                if six.PY3:
                    pack_data = pack_data.decode('Latin-1')

            root = transaction_trace.root
            xray_id = getattr(trace, 'xray_id', None)

            if (xray_id or trace.rum_trace or trace.record_tt):
                force_persist = True
            else:
                force_persist = False

            trace_data.append([root.start_time,
                    root.end_time - root.start_time,
                    trace.path,
                    trace.request_uri,
                    pack_data,
                    trace.guid,
                    None,
                    force_persist,
                    xray_id,])

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
                list(self.__slow_transaction.string_table.values())]

        if self.__settings.debug.log_transaction_trace_payload:
            _logger.debug('Encoding slow transaction data where '
                    'payload=%r.', data)

        with InternalTrace('Supportability/StatsEngine/JSON/Encode/'
                'transaction_sample_data'):

            json_data = json.dumps(data, default=lambda o: list(iter(o)))

        internal_metric('Supportability/StatsEngine/ZLIB/Bytes/'
                'transaction_sample_data', len(json_data))

        with InternalTrace('Supportability/StatsEngine/ZLIB/Compress/'
                'transaction_sample_data'):
            zlib_data = zlib.compress(six.b(json_data))

        with InternalTrace('Supportability/StatsEngine/BASE64/Encode/'
                'transaction_sample_data'):
            pack_data = base64.standard_b64encode(zlib_data)

            if six.PY3:
                pack_data = pack_data.decode('Latin-1')

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
        self.__slow_transaction_old_duration = None
        self.__transaction_errors = []
        self.__metric_ids = {}
        self.__browser_transactions = []
        self.__xray_transactions = []
        self.xray_sessions = {}

        if settings is not None:
            self.__sampled_data_set = SampledDataSet(
                    settings.analytics_events.max_samples_stored)
        else:
            self.__sampled_data_set = SampledDataSet()

    def reset_metric_stats(self):
        """Resets the accumulated statistics back to initial state for
        metric data.

        """

        self.__stats_table = {}

    def reset_sampled_data(self):
        """Resets the accumulated statistics back to initial state for
        sample analytics data.

        """

        if self.__settings is not None:
            self.__sampled_data_set = SampledDataSet(
                    self.__settings.analytics_events.max_samples_stored)
        else:
            self.__sampled_data_set = SampledDataSet()

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
            self.__slow_transaction_old_duration = None

        elif self.__slow_transaction is None:
            self.__slow_transaction_dry_harvests += 1
            agent_limits = self.__settings.agent_limits
            dry_harvests = agent_limits.slow_transaction_dry_harvests
            if self.__slow_transaction_dry_harvests >= dry_harvests:
                self.__slow_transaction_dry_harvests = 0
                self.__slow_transaction_map = {}
                self.__slow_transaction_old_duration = None

        else:
            self.__slow_transaction_dry_harvests = 0
            name = self.__slow_transaction.path
            duration = self.__slow_transaction.duration
            self.__slow_transaction_map[name] = duration

            top_n = self.__settings.transaction_tracer.top_n
            if len(self.__slow_transaction_map) >= top_n:
                self.__slow_transaction_map = {}
                self.__slow_transaction_old_duration = None

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
        self.__browser_transactions = []
        self.__xray_transactions = []

        if self.__settings is not None:
            self.__sampled_data_set = SampledDataSet(
                    self.__settings.analytics_events.max_samples_stored)
        else:
            self.__sampled_data_set = SampledDataSet()

        return stats

    def create_workarea(self):
        """Creates and returns a new empty stats engine object. This would
        be used to distill stats from a single web transaction before then
        merging it back into the parent under a thread lock.

        """

        stats = StatsEngine()

        stats.__settings = self.__settings
        stats.xray_sessions = self.xray_sessions

        return stats

    def merge_metric_stats(self, snapshot, rollback=False):

        """Merges metric data from a snapshot. This is used when merging
        data from a single transaction into main stats engine. It would
        also be done if the sending of the metric data from the harvest
        failed and wanted to keep accumulating it for subsequent
        harvest.

        """

        if not self.__settings:
            return

        if rollback:
            _logger.debug('Performing rollback of metric data into '
                    'subsequent harvest period.')

        # Merge back data into any new data which has been
        # accumulated.

        for key, other in six.iteritems(snapshot.__stats_table):
            stats = self.__stats_table.get(key)
            if not stats:
                self.__stats_table[key] = copy.copy(other)
            else:
                stats.merge_stats(other)

    def merge_other_stats(self, snapshot, merge_traces=True,
            merge_errors=True, merge_sql=True, merge_samples=True,
            rollback=False):

        """Merges non metric data from a snapshot. This would only be
        used when merging data from a single transaction into main
        stats engine. It is assumed the snapshot has newer data and
        that any existing data takes precedence where what should be
        collected is not otherwised based on time.

        """

        if not self.__settings:
            return

        if rollback:
            _logger.debug('Performing rollback of non metric data into '
                    'subsequent harvest period where merge_traces=%r, '
                    'merge_errors=%r, merge_sql=%r and merge_samples=%r.',
                    merge_traces, merge_errors, merge_sql, merge_samples)

        settings = self.__settings

        # Merge in sampled data set. For normal case, as this is merging
        # data from a single transaction, there should only be one. Just
        # to avoid issues, if there is more than one, don't merge. In
        # the case of a rollback merge because of a network issue, then
        # we have to merge differently, restoring the old sampled data
        # and applying the new data over the top. This gives precedence
        # to the newer data.

        if merge_samples:
            if rollback:
                new_sample_data_set = self.__sampled_data_set
                self.__sampled_data_set = snapshot.__sampled_data_set

                for sample in new_sample_data_set.samples:
                    self.__sampled_data_set.add(sample)

            else:
                if snapshot.__sampled_data_set.count == 1:
                    self.__sampled_data_set.add(
                            snapshot.__sampled_data_set.samples[0])

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
            for key, other in six.iteritems(snapshot.__sql_stats_table):
                stats = self.__sql_stats_table.get(key)
                if not stats:
                    if len(self.__sql_stats_table) < maximum:
                        self.__sql_stats_table[key] = copy.copy(other)
                else:
                    stats.merge_stats(other)

        # Restore original slow transaction if slower than any newer slow
        # transaction. Also append any saved transactions corresponding to
        # browser and xray traces, trimming them at the maximum to be kept.

        if merge_traces:

            # Limit number of browser traces to the limit (10)
            # FIXME - snapshot.__browser_transactions has only one element. So
            # we can use the following code:
            #
            # maximum = settings.agent_limits.browser_transactions
            # if len(self.__browser_transactions) < maximum:
            #     self.__browser_transactions.extend(
            #                               snapshot.__browser_transactions)

            maximum = settings.agent_limits.browser_transactions
            self.__browser_transactions.extend(snapshot.__browser_transactions)
            self.__browser_transactions = self.__browser_transactions[:maximum]

            # Limit number of xray traces to the limit (10)
            # Spill over traces after the limit should have no x-ray ids. This
            # qualifies the trace to be considered for slow transaction.

            maximum = settings.agent_limits.xray_transactions
            self.__xray_transactions.extend(snapshot.__xray_transactions)
            for txn in self.__xray_transactions[maximum:]:
                txn.xray_id = None
            self.__xray_transactions = self.__xray_transactions[:maximum]

            transaction = snapshot.__slow_transaction

            # If the transaction has an xray_id then it does not qualify to
            # be considered for slow transaction.  This is because in the Core
            # app, there is logic to NOT show TTs with xray ids in the
            # WebTransactions tab. If a TT has xray_id it is only shown under
            # the xray page.

            xray_id = getattr(transaction, 'xray_id', None)
            if transaction and xray_id is None:
                name = transaction.path
                duration = transaction.duration

                slowest = 0
                if self.__slow_transaction:
                    slowest = self.__slow_transaction.duration
                if name in self.__slow_transaction_map:
                    slowest = max(self.__slow_transaction_map[name], slowest)

                if duration > slowest:
                    # We are going to replace the prior slow
                    # transaction. We need to be a bit tricky here. If
                    # we are overriding an existing slow transaction for
                    # a different name, then we need to restore in the
                    # transaction map what the previous slowest duration
                    # was for that, or remove it if there wasn't one.
                    # This is so we do not incorrectly suppress it given
                    # that it was never actually reported as the slowest
                    # transaction.

                    if self.__slow_transaction:
                        if self.__slow_transaction.path != name:
                            if self.__slow_transaction_old_duration:
                                self.__slow_transaction_map[
                                        self.__slow_transaction.path] = (
                                        self.__slow_transaction_old_duration)
                            else:
                                del self.__slow_transaction_map[
                                        self.__slow_transaction.path]

                    if name in self.__slow_transaction_map:
                        self.__slow_transaction_old_duration = (
                                self.__slow_transaction_map[name])
                    else:
                        self.__slow_transaction_old_duration = None

                    self.__slow_transaction = transaction
                    self.__slow_transaction_map[name] = duration

    def merge_custom_metrics(self, metrics):
        """Merges in a set of custom metrics. The metrics should be
        provide as an iterable where each item is a tuple of the metric
        name and the accumulated stats for the metric.

        """

        if not self.__settings:
            return

        for name, other in metrics:
            key = (name, '')
            stats = self.__stats_table.get(key)
            if not stats:
                self.__stats_table[key] = copy.copy(other)
            else:
                stats.merge_stats(other)
