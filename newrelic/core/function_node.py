from collections import namedtuple

import newrelic.core.trace_node

from newrelic.core.metric import TimeMetric

_FunctionNode = namedtuple('_FunctionNode',
        ['group', 'name', 'children', 'start_time', 'end_time',
        'duration', 'exclusive', 'label', 'params'])

class FunctionNode(_FunctionNode):

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        function node as well as all the child nodes.

        """

        name = '%s/%s' % (self.group, self.name)

        yield TimeMetric(name=name, scope='', duration=self.duration,
                exclusive=self.exclusive)

        yield TimeMetric(name=name, scope=root.path,
                duration=self.duration, exclusive=self.exclusive)

        # Now for the children.

        for child in self.children:
            for metric in child.time_metrics(stats, root, self):
                yield metric

    def trace_node(self, stats, root):

        name = '%s/%s' % (self.group, self.name)

        name = root.string_table.cache(name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        root.trace_node_count += 1

        children = []

        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break
            children.append(child.trace_node(stats, root))

        params = self.params or None

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=self.label)
