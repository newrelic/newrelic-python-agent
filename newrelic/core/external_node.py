import urlparse

try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

import newrelic.core.trace_node

from newrelic.core.metric import TimeMetric

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

        yield TimeMetric(name='External/all', scope='',
                duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebTransaction':
            yield TimeMetric(name='External/allWeb', scope='',
                    duration=self.duration, exclusive=self.exclusive)
        else:
            yield TimeMetric(name='External/allOther', scope='',
                    duration=self.duration, exclusive=self.exclusive)

        hostname = self.details.hostname or 'unknown'

        try:
            port = self.details.port
        except:
            port = None

        netloc = port and ('%s:%s' % (hostname, port)) or hostname

        method = self.method or ''

        name = 'External/%s/all' % netloc

        yield TimeMetric(name=name, scope='', duration=self.duration,
                  exclusive=self.exclusive)

        name = 'External/%s/%s/%s' % (netloc, self.library, method)

        yield TimeMetric(name=name, scope='', duration=self.duration,
                exclusive=self.exclusive)

        yield TimeMetric(name=name, scope=root.path,
                duration=self.duration, exclusive=self.exclusive)

    def trace_node(self, stats, root):

        hostname = self.details.hostname or 'unknown'

        try:
            port = self.details.port
        except:
            port = None

        netloc = port and ('%s:%s' % (hostname, port)) or hostname

        method = self.method or ''

        name = 'External/%s/%s/%s' % (netloc, self.library, method)

        name = root.string_table.cache(name)

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
