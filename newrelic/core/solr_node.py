from collections import namedtuple

import newrelic.core.attribute as attribute
import newrelic.core.trace_node

from newrelic.core.node_mixin import GenericNodeMixin
from newrelic.core.metric import TimeMetric
from newrelic.core.attribute_filter import DST_TRANSACTION_SEGMENTS

_SolrNode = namedtuple('_SolrNode',
        ['library', 'command', 'children', 'start_time', 'end_time',
        'duration', 'exclusive', 'guid', 'is_async', 'agent_attributes'])


class SolrNode(_SolrNode, GenericNodeMixin):

    @property
    def name(self):
        return 'SolrClient/%s/%s' % (self.library, self.command)

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        memcache node as well as all the child nodes.

        """
        yield TimeMetric(name='Solr/all', scope='',
                duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebTransaction':
            yield TimeMetric(name='Solr/allWeb', scope='',
                    duration=self.duration, exclusive=self.exclusive)
        else:
            yield TimeMetric(name='Solr/allOther', scope='',
                    duration=self.duration, exclusive=self.exclusive)

        name = 'Solr/%s' % self.command

        yield TimeMetric(name=name, scope='', duration=self.duration,
                  exclusive=self.exclusive)

        yield TimeMetric(name=name, scope=root.path,
                duration=self.duration, exclusive=self.exclusive)

    def trace_node(self, stats, root, connections):
        name = root.string_table.cache(self.name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        children = []

        root.trace_node_count += 1

        # Agent attributes
        params = attribute.resolve_agent_attributes(
                self.agent_attributes,
                root.settings.attribute_filter,
                DST_TRANSACTION_SEGMENTS)

        # Intrinsic attributes override everything
        params['exclusive_duration_millis'] = 1000.0 * self.exclusive

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=None)
