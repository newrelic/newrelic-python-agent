import collections
import itertools
import urlparse

import newrelic.core.metric

_ExternalNode = collections.namedtuple('_ExternalNode',
        ['library', 'url', 'children', 'start_time', 'end_time',
        'duration', 'exclusive'])

class ExternalNode(_ExternalNode):

    def time_metrics(self, root, parent):
        """Return a generator yielding the timed metrics for this
        external node as well as all the child nodes.

        """

        yield newrelic.core.metric.TimeMetric(name='External/all',
            scope='', overflow=None, forced=True, duration=self.duration,
            exclusive=0.0)

        if root.type == 'WebTransaction':
            yield newrelic.core.metric.TimeMetric(name='External/allWeb',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=0.0)
        else:
            yield newrelic.core.metric.TimeMetric(name='External/allOther',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=0.0)

        # Split the parts out of the URL. Can't use attribute
        # style access and instead must use tuple style access
        # as attribute access only added in Python 2.5.

        parts = urlparse.urlparse(self.url)

        host = parts[1] or 'unknown'
        path = parts[2]

        name = 'External/%s/all' % host

        yield newrelic.core.metric.TimeMetric(name=name, scope='',
                overflow=None, forced=False, duration=self.duration,
                exclusive=0.0)

        name = 'External/%s/%s%s' % (host, self.library, path)
        overflow = 'External/*'

        yield newrelic.core.metric.TimeMetric(name=name, scope='',
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=0.0)

        scope = root.path

        yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=0.0)

        # Now for the children.

        for child in self.children:
            for metric in child.time_metrics(root, self):
                yield metric
