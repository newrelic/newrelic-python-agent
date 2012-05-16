import urlparse

try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

import newrelic.core.metric
import newrelic.core.trace_node

_ExternalNode = namedtuple('_ExternalNode',
        ['library', 'url', 'method', 'children', 'start_time', 'end_time',
        'duration', 'exclusive'])

class ExternalNode(_ExternalNode):

    @property
    def details(self):
        if hasattr(self, '_details'):
            return self._details

        self._details = urlparse.urlparse(self.url)

        return self._details

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        external node as well as all the child nodes.

        """

        yield newrelic.core.metric.TimeMetric(name='External/all',
            scope='', overflow=None, forced=True, duration=self.duration,
            exclusive=self.exclusive)

        if root.type == 'WebTransaction':
            yield newrelic.core.metric.TimeMetric(name='External/allWeb',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)
        else:
            yield newrelic.core.metric.TimeMetric(name='External/allOther',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

        hostname = self.details.hostname or 'unknown'
        port = self.details.port

        netloc = port and ('%s:%s' % (hostname, port)) or hostname

        method = self.method or ''

        name = 'External/%s/all' % netloc

        yield newrelic.core.metric.TimeMetric(name=name, scope='',
                overflow=None, forced=False, duration=self.duration,
                exclusive=self.exclusive)

        name = 'External/%s/%s/%s' % (netloc, self.library, method)
        overflow = 'External/*'

        yield newrelic.core.metric.TimeMetric(name=name, scope='',
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=self.exclusive)

        scope = root.path

        yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=self.exclusive)

    def trace_node(self, stats, string_table, root):

        hostname = self.details.hostname or 'unknown'
        port = self.details.port

        netloc = port and ('%s:%s' % (hostname, port)) or hostname

        method = self.method or ''

        name = 'External/%s/%s/%s' % (netloc, self.library, method)

        name = string_table.cache(name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        children = []

        root.trace_node_count += 1

        params = None

        details = self.details
        url = urlparse.urlunsplit((details.scheme, details.netloc,
                details.path, '', ''))

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=url)
