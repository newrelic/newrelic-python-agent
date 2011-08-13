import collections
import itertools
import urlparse

import newrelic.core.metric
import newrelic.core.trace_node

_FunctionNode = collections.namedtuple('_FunctionNode',
        ['group', 'name', 'children', 'start_time', 'end_time',
        'duration', 'exclusive'])

class FunctionNode(_FunctionNode):

    def time_metrics(self, root, parent):
        """Return a generator yielding the timed metrics for this
        function node as well as all the child nodes.

        """

        name = '%s/%s' % (self.group, self.name)
        overflow = '%s/*' % self.group
        scope = root.path

        yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=None)

        # Now for the children.

        for child in self.children:
            for metric in child.time_metrics(root, self):
                yield metric

    def trace_node(self, root):

        name = '%s/%s' % (self.group, self.name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)
        children = [child.trace_node(root) for child in self.children]

        params = None

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children)
