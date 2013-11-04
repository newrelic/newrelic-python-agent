"""This module provides the transaction node type used as root in the
construction of the raw transaction trace hierarchy from which metrics are
then to be generated.

"""

import itertools

from collections import namedtuple

import newrelic.core.error_collector
import newrelic.core.trace_node

from newrelic.core.metric import ApdexMetric, TimeMetric
from newrelic.core.internal_metrics import internal_trace
from newrelic.core.string_table import StringTable

_TransactionNode = namedtuple('_TransactionNode',
        ['settings', 'path', 'type', 'group', 'name', 'request_uri',
        'response_code', 'request_params', 'custom_params', 'queue_start',
        'start_time', 'end_time', 'duration', 'exclusive', 'children',
        'errors', 'slow_sql', 'apdex_t', 'suppress_apdex', 'custom_metrics',
        'parameter_groups', 'guid', 'rum_trace', 'cpu_time', 'suppress_transaction_trace',
        'client_cross_process_id', 'referring_transaction_guid', 'record_tt'])

class TransactionNode(_TransactionNode):

    """Class holding data corresponding to the root of the transaction. All
    the nodes of interest recorded for the transaction are held as a tree
    structure within the 'childen' attribute.

    """

    def __hash__(self):
        return id(self)

    @property
    def string_table(self):
        result = getattr(self, '_string_table', None)
        if result is not None:
            return result
        self._string_table = StringTable()
        return self._string_table

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

            yield TimeMetric(name='HttpDispatcher', scope='',
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

                yield TimeMetric(name='WebFrontend/QueueTime', scope='',
                        duration=queue_wait, exclusive=None)

        # Generate the full transaction metric.

        yield TimeMetric(name=self.path, scope='', duration=self.duration,
                exclusive=self.exclusive)

        # Generate the rollup metric.

        if self.type != 'WebTransaction':
            rollup = '%s/all' % self.type
        else:
            rollup = self.type

        yield TimeMetric(name=rollup, scope='', duration=self.duration,
                exclusive=self.exclusive)

        if self.errors:
            # Generate overall rollup metric indicating if errors present.
            yield TimeMetric(name='Errors/all', scope='', duration=0.0,
                      exclusive=None)

            # Generate individual error metric for transaction.
            yield TimeMetric(name='Errors/%s' % self.path, scope='',
                    duration=0.0, exclusive=None)

            # Generate rollup metric for WebTransaction errors.
            if self.type == 'WebTransaction':
                yield TimeMetric(name='Errors/allWeb', scope='', duration=0.0,
                        exclusive=None)

            # Generate rollup metric for OtherTransaction errors.
            if self.type != 'WebTransaction':
                yield TimeMetric(name='Errors/allOther', scope='',
                        duration=0.0, exclusive=None)

        # Now for the children.

        for child in self.children:
            for metric in child.time_metrics(stats, self, self):
                yield metric

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

        # Generate the full apdex metric.

        if (self.group in ('Uri', 'NormalizedUri') and
                self.name.startswith('/')):
            name = 'Apdex/%s%s' % (self.group, self.name)
        else:
            name = 'Apdex/%s/%s' % (self.group, self.name)

        yield ApdexMetric(name=name, satisfying=satisfying,
                tolerating=tolerating, frustrating=frustrating,
                apdex_t=self.apdex_t)

        # Generate the rollup metric.

        yield ApdexMetric(name='Apdex', satisfying=satisfying,
                tolerating=tolerating, frustrating=frustrating,
                apdex_t=self.apdex_t)

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

        if not self.errors:
            return

        for error in self.errors:
            params = {}
            params["request_uri"] = self.request_uri
            params["stack_trace"] = error.stack_trace
            if self.request_params:
                params["request_params"] = self.request_params
            if self.parameter_groups:
                params["parameter_groups"] = self.parameter_groups

            custom_params = (error.custom_params and dict(
                error.custom_params) or {})

            if self.client_cross_process_id:
                custom_params['client_cross_process_id'] = \
                        self.client_cross_process_id
            if self.referring_transaction_guid:
                custom_params['referring_transaction_guid'] = \
                        self.referring_transaction_guid

            if custom_params:
                params["custom_params"] = custom_params

            yield newrelic.core.error_collector.TracedError(
                    start_time=error.timestamp, path=self.path,
                    message=error.message, type=error.type,
                    parameters=params)

    def trace_node(self, stats, root):

        name = self.path

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        root.trace_node_count += 1

        children = []

        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break
            children.append(child.trace_node(stats, root))

        params = {}

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=None)

    @internal_trace('Supportability/TransactionNode/Calls/transaction_trace')
    def transaction_trace(self, stats, limit):

        self.trace_node_count = 0
        self.trace_node_limit = limit

        start_time = newrelic.core.trace_node.root_start_time(self)
        request_params = self.request_params or None
        custom_params = self.custom_params or None
        parameter_groups = self.parameter_groups or None
        trace_node = self.trace_node(stats, self)

        # Add in special CPU time value for UI to display CPU burn.

        custom_params = custom_params and dict(custom_params) or {}

        # XXX Disable cpu time value for CPU burn as was
        # previously reporting incorrect value and we need to
        # fix it, at least on Linux to report just the CPU time
        # for the executing thread.

        # custom_params['cpu_time'] = self.cpu_time

        if self.client_cross_process_id:
            custom_params['client_cross_process_id'] = \
                    self.client_cross_process_id
        if self.referring_transaction_guid:
            custom_params['referring_transaction_guid'] = \
                    self.referring_transaction_guid

        # There is an additional trace node labelled as 'ROOT'
        # that needs to be inserted below the root node object
        # which is returned. It inherits the start and end time
        # from the actual top node for the transaction.

        root = newrelic.core.trace_node.TraceNode(trace_node[0],
                trace_node[1], 'ROOT', {}, [trace_node], label=None)

        return newrelic.core.trace_node.RootNode(start_time=start_time,
                request_params=request_params, custom_params=custom_params,
                root=root, parameter_groups=parameter_groups)

    def slow_sql_nodes(self, stats):
        for item in self.slow_sql:
            yield item.slow_sql_node(stats, self)
