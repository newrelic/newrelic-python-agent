import collections
import itertools
import urlparse

import newrelic.core.metric

_FunctionNode = collections.namedtuple('_FunctionNode',
        ['group', 'name', 'children', 'start_time', 'end_time',
        'duration', 'exclusive'])

class FunctionNode(_FunctionNode):

    def time_metrics(self, root, parent):
        """Return a generator yielding the timed metrics for this
        function node as well as all the child nodes.

        """

        name = '%s/%s' % (self.group, self.name)
        overflow = '%s/*' % self.group
        scope = root.path

        yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                overflow=overflow, forced=False, duration=self.duration,
                exclusive=None)

        # Now for the children.

        for child in self.children:
            for metric in child.time_metrics(root, self):
                yield metric
