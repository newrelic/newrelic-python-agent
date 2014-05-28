from collections import namedtuple

import newrelic.core.trace_node

from newrelic.core.metric import TimeMetric

_FunctionNode = namedtuple('_FunctionNode',
        ['group', 'name', 'children', 'start_time', 'end_time',
        'duration', 'exclusive', 'label', 'params', 'rollup'])

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

        # Generate a rollup metric if one has been specified.
        #
        # We actually implement two cases here. If the rollup name ends
        # with /all, then we implement the old style, which is to
        # generate an unscoped /all metric, plus if a web transaction
        # then /allWeb. For non web transaction also generate /allOther.
        #
        # If not the old style, but new style, the rollup metric
        # has scope corresponding to the transaction type.
        #
        # For the old style it must match one of the existing rollup
        # categories recognised by the UI. For the new, we can add our
        # own rollup categories.

        if self.rollup:
            if self.rollup.endswith('/all'):
                yield TimeMetric(name=self.rollup, scope='',
                        duration=self.duration, exclusive=None)

                if root.type == 'WebTransaction':
                    yield TimeMetric(name=self.rollup+'Web', scope='',
                            duration=self.duration, exclusive=None)
                else:
                    yield TimeMetric(name=self.rollup+'Other', scope='',
                            duration=self.duration, exclusive=None)

            else:
                yield TimeMetric(name=self.rollup, scope=root.type,
                        duration=self.duration, exclusive=None)

        # Now for the children.

        for child in self.children:
            for metric in child.time_metrics(stats, root, self):
                yield metric

    def trace_node(self, stats, root, connections):

        name = '%s/%s' % (self.group, self.name)

        name = root.string_table.cache(name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        root.trace_node_count += 1

        children = []

        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break
            children.append(child.trace_node(stats, root, connections))

        params = self.params or None

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=self.label)
