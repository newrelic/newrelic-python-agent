try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

import newrelic.core.metric
import newrelic.core.trace_node

_MemcacheNode = namedtuple('_MemcacheNode',
        ['command', 'children', 'start_time', 'end_time', 'duration',
        'exclusive'])

class MemcacheNode(_MemcacheNode):

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        memcache node as well as all the child nodes.

        """

        yield newrelic.core.metric.TimeMetric(name='Memcache/all',
            scope='', overflow=None, forced=True, duration=self.duration,
            exclusive=self.exclusive)

        if root.type == 'WebTransaction':
            yield newrelic.core.metric.TimeMetric(name='Memcache/allWeb',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)
        else:
            yield newrelic.core.metric.TimeMetric(name='Memcache/allOther',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

        name = 'Memcache/%s' % self.command
        overflow = 'Memcache/*'

        yield newrelic.core.metric.TimeMetric(name=name, scope='',
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=self.exclusive)

        scope = root.path

        yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=self.exclusive)

        # XXX Ignore the children as this should be a terminal node.

        #for child in self.children:
        #    for metric in child.time_metrics(stats, root, self):
        #        yield metric

    def trace_node(self, stats, string_table, root):

        name = 'Memcache/%s' % self.command

        name = string_table.cache(name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        # XXX Ignore the children as this should be a terminal node.

        #children = [child.trace_node(stats, string_table, root) for
        #            child in self.children]
        children = []

        root.trace_node_count += 1

        params = None

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=None)
