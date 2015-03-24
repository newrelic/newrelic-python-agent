from collections import namedtuple

import newrelic.core.trace_node

from newrelic.core.metric import TimeMetric

_DatastoreNode = namedtuple('_DatastoreNode',
        ['product',  'target', 'operation', 'children', 'start_time',
        'end_time', 'duration', 'exclusive'])

class DatastoreNode(_DatastoreNode):

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        database node as well as all the child nodes.

        """

        product = self.product
        target = self.target
        operation = self.operation or 'other'

        # Rollup metrics

        yield TimeMetric(name='Datastore/all', scope='',
                duration=self.duration, exclusive=self.exclusive)

        yield TimeMetric(name='Datastore/%s/all' % product, scope='',
                duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebTransaction':
            yield TimeMetric(name='Datastore/allWeb', scope='',
                    duration=self.duration, exclusive=self.exclusive)

            yield TimeMetric(name='Datastore/%s/allWeb' % product, scope='',
                    duration=self.duration, exclusive=self.exclusive)

        else:
            yield TimeMetric(name='Datastore/allOther', scope='',
                    duration=self.duration, exclusive=self.exclusive)

            yield TimeMetric(name='Datastore/%s/allOther' % product, scope='',
                    duration=self.duration, exclusive=self.exclusive)

        # Statement metrics.

        if target:
            name = 'Datastore/statement/%s/%s/%s' % (product, target,
                    operation)

            yield TimeMetric(name=name, scope='', duration=self.duration,
                    exclusive=self.exclusive)

            yield TimeMetric(name=name, scope=root.path,
                duration=self.duration, exclusive=self.exclusive)

        # Operation metrics.

        name = 'Datastore/operation/%s/%s' % (product, operation)

        yield TimeMetric(name=name, scope='', duration=self.duration,
                exclusive=self.exclusive)

        if not target:
            yield TimeMetric(name=name, scope=root.path,
                    duration=self.duration, exclusive=self.exclusive)

    def trace_node(self, stats, root, connections):
        product = self.product
        target = self.target
        operation = self.operation or 'other'

        if target:
            name = 'Datastore/statement/%s/%s/%s' % (product, target,
                    operation)
        else:
            name = 'Datastore/operation/%s/%s' % (product, operation)

        name = root.string_table.cache(name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        children = []

        root.trace_node_count += 1

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=None, children=children,
                label=None)
