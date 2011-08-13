import collections
import itertools
import urlparse

import newrelic.core.metric
import newrelic.core.trace_node

_MemcacheNode = collections.namedtuple('_MemcacheNode',
        ['command', 'children', 'start_time', 'end_time', 'duration',
        'exclusive'])

class MemcacheNode(_MemcacheNode):

    def time_metrics(self, root, parent):
        """Return a generator yielding the timed metrics for this
        memcache node as well as all the child nodes.

        """

        yield newrelic.core.metric.TimeMetric(name='Memcache/all',
            scope='', overflow=None, forced=True, duration=self.duration,
            exclusive=None)

        if root.type == 'WebTransaction':
            yield newrelic.core.metric.TimeMetric(name='Memcache/allWeb',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=None)
        else:
            yield newrelic.core.metric.TimeMetric(name='Memcache/allOther',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=None)

        # Note that it is 'MemCache' here and not 'Memcache'.

        name = 'MemCache/%s' % self.command
        overflow = 'Memcache/*'

        yield newrelic.core.metric.TimeMetric(name=name, scope='',
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=None)

        scope = root.path

        yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=None)

        # Now for the children.

        for child in self.children:
            for metric in child.time_metrics(root, self):
                yield metric

    def trace_node(self, root):

        # Note that it is 'MemCache' here and not 'Memcache'.

        name = 'MemCache/%s' % self.command

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)
        children = [child.trace_node(root) for child in self.children]

        params = None

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children)
