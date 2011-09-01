import collections
import itertools
import urlparse

import newrelic.core.metric
import newrelic.core.trace_node

_ExternalNode = collections.namedtuple('_ExternalNode',
        ['library', 'url', 'children', 'start_time', 'end_time',
        'duration', 'exclusive'])

class ExternalNode(_ExternalNode):

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

        # Split the parts out of the URL. Can't use attribute
        # style access and instead must use tuple style access
        # as attribute access only added in Python 2.5.

        parts = urlparse.urlparse(self.url)

        host = parts[1] or 'unknown'
        path = parts[2]

        name = 'External/%s/all' % host

        yield newrelic.core.metric.TimeMetric(name=name, scope='',
                overflow=None, forced=False, duration=self.duration,
                exclusive=self.exclusive)

        name = 'External/%s/%s%s' % (host, self.library, path)
        overflow = 'External/*'

        yield newrelic.core.metric.TimeMetric(name=name, scope='',
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=self.exclusive)

        scope = root.path

        yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=self.exclusive)

        # Now for the children.

	# TODO Above exclusive times don't take into
	# consideration children if any existed. Still need to
	# work out how such children to this nodes is meant to
	# work.

        for child in self.children:
            for metric in child.time_metrics(stats, root, self):
                yield metric

    def trace_node(self, stats, root):

        # FIXME This duplicates what is done above. Need to cache.

        parts = urlparse.urlparse(self.url)

        host = parts[1] or 'unknown'
        path = parts[2]

        name = 'External/%s/%s%s' % (host, self.library, path)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)
        children = [child.trace_node(stats, root) for child in self.children]

        params = None

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children)
