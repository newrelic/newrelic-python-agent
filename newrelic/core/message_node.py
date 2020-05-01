from collections import namedtuple

import newrelic.core.trace_node

from newrelic.core.node_mixin import GenericNodeMixin
from newrelic.core.metric import TimeMetric

_MessageNode = namedtuple('_MessageNode',
        ['library', 'operation', 'children', 'start_time',
        'end_time', 'duration', 'exclusive', 'destination_name',
        'destination_type', 'params', 'guid',
        'agent_attributes', 'user_attributes'])


class MessageNode(_MessageNode, GenericNodeMixin):

    @property
    def name(self):
        name = 'MessageBroker/%s/%s/%s/Named/%s' % (self.library,
                self.destination_type, self.operation, self.destination_name)
        return name

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        messagebroker node as well as all the child nodes.

        """
        name = self.name

        # Unscoped metric

        yield TimeMetric(name=name, scope='',
                duration=self.duration, exclusive=self.exclusive)

        # Scoped metric

        yield TimeMetric(name=name, scope=root.path,
                duration=self.duration, exclusive=self.exclusive)

    def trace_node(self, stats, root, connections):
        name = root.string_table.cache(self.name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        children = []

        root.trace_node_count += 1

        params = self.get_trace_segment_params(
                root.settings, params=self.params)

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=None)
