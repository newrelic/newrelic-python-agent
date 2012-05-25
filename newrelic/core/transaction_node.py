"""This module provides the transaction node type used as root in the
construction of the raw transaction trace hierarchy from which metrics are
then to be generated.

"""

import itertools
import urlparse

try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

import newrelic.core.metric
import newrelic.core.error_collector
import newrelic.core.trace_node

from newrelic.core.internal_metrics import internal_trace

_TransactionNode = namedtuple('_TransactionNode',
        ['settings', 'path', 'type', 'group', 'name', 'request_uri',
        'response_code', 'request_params', 'custom_params', 'queue_start',
        'start_time', 'end_time', 'duration', 'exclusive', 'children',
        'errors', 'slow_sql', 'apdex_t', 'suppress_apdex', 'custom_metrics',
        'parameter_groups'])

class TransactionNode(_TransactionNode):

    """Class holding data corresponding to the root of the transaction. All
    the nodes of interest recorded for the transaction are held as a tree
    structure within the 'childen' attribute. Errors raised can recorded
    are within the 'errors' attribute. Nodes corresponding to slow SQL
    requests are available directly in the 'slow_sql' attribute.

    """

    @internal_trace('Supportability/TransactionNode/Calls/time_metrics')
    def time_metrics(self, stats):
        """Return a generator yielding the timed metrics for the
        top level web transaction as well as all the child nodes.

        """

        # TODO What to do about a transaction where the name is
        # None. In the PHP agent it replaces it with an
        # underscore for timed metrics and continues. For an
        # apdex metric the PHP agent ignores it however. For now
        # we just ignore it.

        if not self.name:
            return

        if self.type == 'WebTransaction':
            # Report time taken by request dispatcher. We don't
            # know upstream time distinct from actual request
            # time so can't report time exclusively in the
            # dispatcher.

            # TODO Technically could work this out with the
            # modifications in Apache/mod_wsgi to mark start of
            # the request. How though does that differ to queue
            # time. Need to clarify purpose of HttpDispatcher
            # and how the exclusive component would appear in
            # the overview graphs.

            # TODO The PHP agent doesn't mark this as forced but
            # possibly it should be. Would always be included in
            # PHP agent as comes first in the metrics generated
            # for a request and wouldn't get removed when metric
            # limit reached.

            #yield newrelic.core.metric.TimeMetric(name='HttpDispatcher',
            #        scope='', overflow=None, forced=False,
            #        duration=self.duration, exclusive=None)

            yield newrelic.core.metric.TimeMetric(name='HttpDispatcher',
                    scope='', overflow=None, forced=True,
                    duration=self.duration, exclusive=None)

            # Upstream queue time within any web server front end.

            # TODO How is this different to the exclusive time
            # component for the dispatcher above.

            # TODO Not yet dealing with additional headers for
            # tracking time through multiple front ends.

            if self.queue_start != 0:
                queue_wait = self.start_time - self.queue_start
                if queue_wait < 0:
                    queue_wait = 0

                yield newrelic.core.metric.TimeMetric(
                        name='WebFrontend/QueueTime', scope='',
                        overflow=None, forced=True, duration=queue_wait,
                        exclusive=None)

        # Generate the full transaction metric.

        name = self.path

        yield newrelic.core.metric.TimeMetric(name=name, scope='',
                overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

        # Generate the rollup metric.

        if self.type != 'WebTransaction':
            rollup = '%s/all' % self.type
        else:
            rollup = self.type

        yield newrelic.core.metric.TimeMetric(name=rollup, scope='',
                overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

	# Generate metric indicating if errors present. Only do
	# this for web transactions and not anything else.

        if self.type == 'WebTransaction' and self.errors:
            yield newrelic.core.metric.TimeMetric(name='Errors/all',
                    scope='', overflow=None, forced=True, duration=0.0,
                    exclusive=None)

        # Now for the children.

        for child in self.children:
            for metric in child.time_metrics(stats, self, self):
                yield metric

    @internal_trace('Supportability/TransactionNode/Calls/apdex_metrics')
    def apdex_metrics(self, stats):
        """Return a generator yielding the apdex metrics for this node.

        """

        if not self.name:
            return

        if self.suppress_apdex:
            return

        # The apdex metrics are only relevant to web transactions.

        if self.type != 'WebTransaction':
            return

        # The magic calculations based on apdex_t. The apdex_t
        # is based on what was in place at the start of the
        # transaction. This could have changed between that
        # point in the request and now.

        satisfying = 0
        tolerating = 0
        frustrating = 0

        if self.errors:
            frustrating = 1
        else:
            if self.duration <= self.apdex_t:
                satisfying = 1
            elif self.duration <= 4 * self.apdex_t:
                tolerating = 1
            else:
                frustrating = 1

        # Generate the full apdex metric. In this case we
        # need to specific an overflow metric for case where
        # too many metrics have been generated and want to
        # stick remainder in a bucket.

        # TODO Should the apdex metric path only include the
        # first segment of group? That is, only the top level
        # category and not any sub categories.

        if self.group in ['Uri', 'NormalizedUri'] and self.name[:1] == '/':
            name = 'Apdex/%s%s' % (self.group, self.name)
        else:
            name = 'Apdex/%s/%s' % (self.group, self.name)

        overflow = 'Apdex/%s/*' % self.group

        yield newrelic.core.metric.ApdexMetric(name=name,
                overflow=overflow, forced=False, satisfying=satisfying,
                tolerating=tolerating, frustrating=frustrating)

        # Generate the rollup metric.

        yield newrelic.core.metric.ApdexMetric(name='Apdex',
                overflow=None, forced=True, satisfying=satisfying,
                tolerating=tolerating, frustrating=frustrating)

    @internal_trace('Supportability/TransactionNode/Calls/value_metrics')
    def value_metrics(self, stats):
        """Return a generator yielding any custom metrics recorded
        against this transaction.

        """

        for name, value in self.custom_metrics:
            yield newrelic.core.metric.ValueMetric(name=name, value=value)

    @internal_trace('Supportability/TransactionNode/Calls/error_details')
    def error_details(self):
        """Return a generator yielding the details for each unique error
        captured during this transaction.

        """

        # TODO There is no attempt so far to eliminate duplicates.
        # Duplicates could be eliminated based on exception type
        # and message or exception type and file name/line number
        # presuming the latter are available. Right now the file
        # name and line number aren't captured so can't rely on it.

        # TODO There are no constraints in place on what keys/values
        # can be in params dictionaries. Need to convert values to
        # strings at some point.

        for error in self.errors:
            params = {}
            params["request_uri"] = self.request_uri
            params["stack_trace"] = error.stack_trace
            if self.request_params:
                params["request_params"] = self.request_params
            if self.parameter_groups:
                params["parameter_groups"] = self.parameter_groups
            if error.custom_params:
                if self.response_code != 0:
                    error.custom_params['STATUS'] = str(self.response_code)
                params["custom_params"] = error.custom_params

            yield newrelic.core.error_collector.TracedError(
                    start_time=error.timestamp, path=self.path,
                    message=error.message, type=error.type,
                    parameters=params)

    def trace_node(self, stats, string_table, root):

        name = self.path

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        #children = [child.trace_node(stats, string_table, root) for
        #            child in self.children]

        root.trace_node_count += 1

        children = []

        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break
            children.append(child.trace_node(stats, string_table, root))

        params = {}

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=None)

    @internal_trace('Supportability/TransactionNode/Calls/transaction_trace')
    def transaction_trace(self, stats, string_table, limit):

        self.trace_node_count = 0
        self.trace_node_limit = limit

        start_time = newrelic.core.trace_node.root_start_time(self)
        request_params = self.request_params or None
        custom_params = self.custom_params or None
        parameter_groups = self.parameter_groups or None
        trace_node = self.trace_node(stats, string_table, self)

	# There is an additional trace node labelled as 'ROOT'
	# that needs to be inserted below the root node object
        # which is returned. It inherits the start and end time
        # from the actual top node for the transaction.

        root = newrelic.core.trace_node.TraceNode(trace_node[0],
                trace_node[1], 'ROOT', {}, [trace_node], label=None)

        return newrelic.core.trace_node.RootNode(start_time=start_time,
                request_params=request_params, custom_params=custom_params,
                root=root, parameter_groups=parameter_groups)

    @internal_trace('Supportability/TransactionNode/Calls/slow_sql_nodes')
    def slow_sql_nodes(self, stats):
        for item in self.slow_sql:
            yield item.slow_sql_node(stats, self)

