from collections import namedtuple

import newrelic.core.trace_node

from newrelic.core.metric import TimeMetric

_DatastoreNode = namedtuple('_DatastoreNode',
        ['product',  'target', 'operation', 'children', 'start_time',
        'end_time', 'duration', 'exclusive'])

class DatastoreNode(_DatastoreNode):

    # TODO: Get final placeholder for target, when spec is final.
    target_default = '*'
    operation_default = 'other'

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        database node as well as all the child nodes.

        """

        product = self.product
        target = self.target or self.target_default
        operation = self.operation or self.operation_default

        # Private rollup metric. Not used by APM, but it's helpful for
        # us to calculate databaseDuration and databaseCallCount for the
        # Transaction Event.

        yield TimeMetric(name='Supportability/Datastore/all', scope='',
                duration=self.duration, exclusive=self.exclusive)

        # Product level rollup metrics

        name = 'Datastore/%s/all' % product

        yield TimeMetric(name=name, scope='',
                duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebTransaction':

            name = 'Datastore/%s/allWeb' % product

            yield TimeMetric(name=name, scope='',
                    duration=self.duration, exclusive=self.exclusive)
        else:

            name = 'Datastore/%s/allOther' % product

            yield TimeMetric(name=name, scope='',
                    duration=self.duration, exclusive=self.exclusive)

        # Statement metrics

        name = 'Datastore/statement/%s/%s/%s' % (product, target, operation)

        yield TimeMetric(name=name, scope='', duration=self.duration,
                exclusive=self.exclusive)

        yield TimeMetric(name=name, scope=root.path,
            duration=self.duration, exclusive=self.exclusive)

        # Operation metrics

        name = 'Datastore/operation/%s/%s' % (product, operation)

        yield TimeMetric(name=name, scope='', duration=self.duration,
                exclusive=self.exclusive)

    def trace_node(self, stats, root, connections):

        product = self.product
        target = self.target or self.target_default
        operation = self.operation or self.operation_default

        name = 'Datastore/%s/%s/%s' % (product, target, operation)

        name = root.string_table.cache(name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        children = []

        root.trace_node_count += 1

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=None, children=children,
                label=None)
