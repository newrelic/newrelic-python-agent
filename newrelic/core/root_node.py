from collections import namedtuple

import newrelic.core.trace_node
from newrelic.core.node_mixin import GenericNodeMixin
from newrelic.core.attribute import resolve_user_attributes

from newrelic.packages import six

_RootNode = namedtuple('_RootNode',
        ['name', 'children', 'start_time', 'end_time', 'exclusive',
        'duration', 'guid', 'agent_attributes', 'user_attributes',
        'path', 'trusted_parent_span', 'tracing_vendors',])


class RootNode(_RootNode, GenericNodeMixin):
    def span_event(self, *args, **kwargs):
        span = super(RootNode, self).span_event(*args, **kwargs)
        i_attrs = span[0]
        i_attrs['nr.entryPoint'] = True
        if self.trusted_parent_span:
            i_attrs['trustedParentId'] = self.trusted_parent_span
        if self.tracing_vendors:
            i_attrs['tracingVendors'] = self.tracing_vendors
        return span

    def trace_node(self, stats, root, connections):

        name = self.path

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        root.trace_node_count += 1

        children = []

        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break
            children.append(child.trace_node(stats, root, connections))

        params = self.get_trace_segment_params(root.settings)

        return newrelic.core.trace_node.TraceNode(
                start_time=start_time,
                end_time=end_time,
                name=name,
                params=params,
                children=children,
                label=None)
