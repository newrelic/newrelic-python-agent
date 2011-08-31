"""The stats engine is what collects the accumulated transactions metrics,
details of errors and slow transactions. There is one instance of the stats
engine per application. This will be cleared upon each succesful harvest of
data whereby it is sent to the core application.

"""

import operator
import copy

import newrelic.core.metric

class ApdexStats(list):

    """Bucket for accumulating apdex metrics.
    
    """
    
    # Is based on a list of length 6 as all metrics are sent to the core
    # application as that and list as base class means it encodes direct
    # to JSON as we need it. In this case only the first 3 entries are
    # used though with remainder being 0.

    def __init__(self):
        super(ApdexStats, self).__init__([0, 0, 0, 0, 0, 0])

    satisfying = property(operator.itemgetter(0))
    tolerating = property(operator.itemgetter(1))
    frustrating = property(operator.itemgetter(2))

    def merge_stats(self, other):
        """Merge data from another instance of this object."""

        self[0] += other[0]
        self[1] += other[1]
        self[2] += other[2]

    def merge_metric(self, metric):
        """Merge data from an apdex metric object."""

        self[0] += metric.satisfying
        self[1] += metric.tolerating
        self[2] += metric.frustrating

class TimeStats(list):

    """Bucket for accumulating time and value metrics.
    
    """

    # Is based on a list of length 6 as all metrics are sent to the core
    # application as that and list as base class means it encodes direct
    # to JSON as we need it.

    def __init__(self):
        super(TimeStats, self).__init__([0, 0, 0, 0, 0, 0])

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

    def merge_metric(self, metric):
        """Merge data from a time or value metric object."""

        if hasattr(metric, 'duration') and hasattr(metric, 'exclusive'):
            duration = metric.duration
            exclusive = metric.exclusive

            if exclusive is None:
                exclusive = duration
        else:
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
        self.__slow_transaction = None
        self.__transaction_errors = []
        self.__sql_traces = []
        self.__metric_ids = {}

    @property
    def slow_transaction(self):
	"""Returns a reference to the details of the slowest transaction
	for the reporting period or None if one hasn't been recorded.

        """

        return self.__slow_transaction

    @property
    def transaction_errors(self):
	"""Returns a reference to a list containing any errors collected
	during the reporting period.

        """

        return self.__transaction_errors

    @property
    def sql_traces(self):
	"""Returns a reference to a list containing any sql traces
	collected during the reporting period.

        """

        return self.__sql_traces

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

    def record_apdex_metric(self, metric):
	"""Record a single apdex metric, merging the data with any data
	from prior apdex metrics with the same name.

        """

        if not self.__settings:
            return

        key = (metric.name, None)
        stats = self.__stats_table.get(key)
        if stats is None:
            stats = ApdexStats()
            self.__stats_table[key] = stats
        stats.merge_metric(metric)

    def record_apdex_metrics(self, metrics):
	"""Record the apdex metrics supplied by the iterable for a
	single transaction, merging the data with any data from prior
	apdex metrics with the same name.

        """

        if not self.__settings:
            return

        for metric in metrics:
            self.record_apdex_metric(metric)

    def record_time_metric(self, metric, overflow=False):
	"""Record a single time metric, merging the data with any data
	from prior time metrics with the same name and scope. When
        overflow is true then the overflow metric name is used rather
        than the original metric name.

        """

        if not self.__settings:
            return

	# Scope is forced to be empty string if None as
	# scope of None is reserved for apdex metrics.

        if overflow:
            key = (metric.overflow, metric.scope or '')
        else:
            key = (metric.name, metric.scope or '')
        stats = self.__stats_table.get(key)
        if stats is None:
            stats = TimeStats()
            self.__stats_table[key] = stats
        stats.merge_metric(metric)

    def record_time_metrics(self, metrics, threshold, minimum, maximum):
	"""Record the time metrics supplied by the iterable for a single
	transaction, merging the data with any data from prior time
	metrics with the same name and scope. For metrics which are not
	being forced and which define an overflow metric, a minimum
	number of unique metrics will be reported. This will be those with
	longest exclusive time. Beyond that mininum number of unique
	metrics, subsequent metrics will be distinctly reported if they
	have exclusive time greater than the threshold, stopping when a
	maximum number of unique metrics have been recorded. After that the
	metrics will be reported against any defined overflow metric name
	instead.

        """

        if not self.__settings:
            return

        if threshold:
            metrics = reversed(sorted(metrics, key=lambda x: x.exclusive))

            include = set()

            # Metric types we should never rollup into overflow.

            exclude = set(['Database', 'External', 'MemCache'])

            for metric in metrics:
                overflow = False

                if metric.name.split('/')[0] not in exclude:

                    if not metric.forced and metric.overflow:

                        if (metric.name, metric.scope) in include:
                            pass

                        elif len(include) < minimum:
                            pass

                        elif maximum > 0 and len(include) > maximum:
                            overflow = True

                        elif metric.exclusive < threshold:
                            overflow = True

                if not overflow:
                    include.add((metric.name, metric.scope))

                self.record_time_metric(metric, overflow=overflow)

        else:
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
        stats.merge_metric(metric)

    def record_value_metrics(self, metrics):
	"""Record the value metrics supplied by the iterable, merging
	the data with any data from prior value metrics with the same
        name.

        """

        if not self.__settings:
            return

        for metric in metrics:
            self.record_value_metric(metric)

    def record_transaction(self, transaction):
        """Record any apdex and time metrics for the transaction as
        well as any errors which occurred for the transaction. If the
        transaction qualifies to become the slow transaction remember
        it for later.

        """

        if not self.__settings:
            return

        error_collector = self.__settings.error_collector
        transaction_tracer = self.__settings.transaction_tracer
        transaction_metrics = self.__settings.transaction_metrics

        # FIXME The application object perhaps needs to maintain an
        # activation counter. This would be incremented after each
        # connect to core application and updated server side
        # configuration available. The counter number should then be
        # pushed into the application specific settings object and the
        # higher level instrumentation layer should then supply the
        # counter value in the TransactionNode root object for the raw
        # transaction data. That way the code here could make a decision
        # whether the data should be thrown away as it relates to a
        # transaction that started when the application was previously
        # active, but got restarted in between then and when the
        # transaction completed. If we don't do this then we could push
        # through transaction data accumulated based on an old set of
        # application specific configuration settings. This may not be
        # an issue given in most cases the server side configuration
        # wouldn't change but should be considered. No harm in adding
        # the counter even if not ultimately needed. The core
        # application could even be what doles out the counter or
        # identifying value for that configuration snapshot and record
        # it against the agent run details stored in core application
        # database rather than it be generated internally using a
        # counter. The value could change on each request or only
        # increment when server side sees a change in server side
        # application configuration. If only changes when configuration
        # changes, wouldn't matter then that request started with one
        # configuration and finished after application had been
        # restarted.

	# Record the apdex and time metrics generated from the
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

        self.record_apdex_metrics(transaction.apdex_metrics())

        minimum = transaction_metrics.overflow_minimum
        maximum = transaction_metrics.overflow_maximum

        threshold = transaction_metrics.overflow_threshold
        threshold = threshold * transaction.duration

        self.record_time_metrics(transaction.time_metrics(),
                threshold, minimum, maximum)

        # Capture any errors if error collection is enabled.

        if error_collector.enabled:
            self.__transaction_errors.extend(transaction.error_details())

        # Capture any sql traces if transaction tracer enabled.

        # FIXME What needs to be done here to convert the sql
        # nodes of the transaction into form to be held by the
        # sql_traces attribute ready for sending to the core
        # application. Assumed for moment that is sequence of
        # dictionary objects like for error details and can just
        # add them into the end of the list.

        if transaction_tracer.enabled:
            self.__sql_traces.extend(transaction.sql_traces())

	# Remember as slowest transaction if transaction tracer
	# is enabled, it is over the threshold and slower than
	# any existing transaction.

        threshold = transaction_tracer.transaction_threshold

        if transaction_tracer.enabled:
            if transaction.duration >= threshold:
                if self.__slow_transaction is None:
                    self.__slow_transaction = transaction
                elif transaction.duration >= self.__slow_transaction.duration:
                    self.__slow_transaction = transaction

    def metric_data(self):
	"""Returns a generator yielding the low level metric data for
	sending to the core application pertaining to the reporting
	period. This consists of tuple pairs where first is dictionary
	with name and scope keys with corresponding values, or integer
	identifier if metric had an entry in dictionary mapping metric
	(name, scope) as supplied from core application. The second is
        the list of accumulated metric data, the list always being of
        length 6.

        """

        for key, value in self.__stats_table.iteritems():
            if key not in self.__metric_ids:
                key = dict(name=key[0], scope=key[1])
            else:
                key = self.__metric_ids[key]
            yield key, value

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
        self.__slow_transaction = None
        self.__transaction_errors = []
        self.__sql_traces = []
        self.__metric_ids = {}

    def create_snapshot(self):
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

	# We retain the table of metric IDs. This should be okay
	# for continuing connection. If connection is lost then
	# reset_engine() above would be called and it would be
        # all thrown away so no chance of following through with
        # incorrect mappings. Possibly even fine to retain them
        # over a reset but need to verify that.

        self.__stats_table = {}
        self.__slow_transaction = None
        self.__transaction_errors = []
        self.__sql_traces = []

        return stats

    def merge_snapshot(self, snapshot):
        """Merges back all the data from a snapshot. This would be done
        if the sending of the metric data from the harvest failed and
        wanted to keep accumulating it for subsequent harvest. If failure
        occurred in sending details or errors or slow transaction, then
        those should be thrown away and this method not called, else you
        would end up sending base metric data multiple times.

        """

	# Merge back data into any new data which has been
	# accumulated.

        # FIXME Should all metrics always be merged back in?

        for key, other in snapshot.__stats_table.iteritems():
            stats = self.__stats_table.get(key)
            if not stats:
                self.__stats_table[key] = copy.copy(other)
            else:
                stats.merge_stats(other)

        # Insert original error details at start of any new
        # ones to maintain time based order.

        # FIXME Should all accumulated errors be retained
        # or should they be aged out. For now throw away
        # the older ones for period that reporting failed.

        #self.__transaction_errors[:0] = snapshot.transaction_errors

        # Insert original sql traces at start of any new
        # ones to maintain time based order.

        # FIXME Should all accumulated sql traces be retained
        # or should they be aged out. For now throw away
        # the older ones for period that reporting failed.

        #self.__sql_traces[:0] = snapshot.sql_traces

        # Restore original slow transaction if slower than
        # any newer slow transaction.

        transaction = snapshot.__slow_transaction

        if self.slow_transaction is None:
            self.__slow_transaction = transaction
        elif transaction.duration > self.slow_transaction.duration:
            self.__slow_transaction = transaction
