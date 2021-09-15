# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple

import newrelic.core.trace_node

from newrelic.core.metric import TimeMetric
from newrelic.core.node_mixin import GenericNodeMixin


_GraphQLOperationNode = namedtuple('_GraphQLNode',
    ['operation_type', 'operation_name', 'deepest_path', 'graphql', 
    'children', 'start_time', 'end_time', 'duration', 'exclusive', 'guid',
    'agent_attributes', 'user_attributes', 'product'])

_GraphQLResolverNode = namedtuple('_GraphQLNode',
    ['field_name', 'children', 'start_time', 'end_time', 'duration', 
    'exclusive', 'guid', 'agent_attributes', 'user_attributes', 'product'])

class GraphQLNodeMixin(GenericNodeMixin):
    def trace_node(self, stats, root, connections):
        name = root.string_table.cache(self.name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        root.trace_node_count += 1

        children = []

        # Now for the children

        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break
            children.append(child.trace_node(stats, root, connections))

        # Agent attributes
        params = self.get_trace_segment_params(root.settings)

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=None)

class GraphQLResolverNode(_GraphQLResolverNode, GraphQLNodeMixin):
    @property
    def name(self):
        field_name = self.field_name or "<unknown>"
        product = self.product

        name = 'GraphQL/resolve/%s/%s' % (product, field_name)

        return name

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        database node as well as all the child nodes.
        """

        field_name = self.field_name or "<unknown>"
        product = self.product

        # Determine the scoped metric

        field_resolver_metric_name = 'GraphQL/resolve/%s/%s' % (product, field_name)

        yield TimeMetric(name=field_resolver_metric_name, scope=root.path, duration=self.duration,
                         exclusive=self.exclusive)

        yield TimeMetric(name=field_resolver_metric_name, scope='', duration=self.duration,
                         exclusive=self.exclusive)

        # Now for the children

        for child in self.children:
            for metric in child.time_metrics(stats, root, self):
                yield metric


class GraphQLOperationNode(_GraphQLOperationNode, GraphQLNodeMixin):
    @property
    def name(self):
        operation_type = self.operation_type
        operation_name = self.operation_name
        deepest_path = self.deepest_path
        product = self.product

        name = 'GraphQL/operation/%s/%s/%s/%s' % (product, operation_type,
                operation_name, deepest_path)

        return name

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        database node as well as all the child nodes.

        """

        operation_type = self.operation_type
        operation_name = self.operation_name
        deepest_path = self.deepest_path
        product = self.product

        # Determine the scoped metric

        operation_metric_name = 'GraphQL/operation/%s/%s/%s/%s' % (product,
                operation_type, operation_name, deepest_path)

        scoped_metric_name = operation_metric_name

        yield TimeMetric(name=scoped_metric_name, scope=root.path,
                    duration=self.duration, exclusive=self.exclusive)

        # Unscoped rollup metrics

        yield TimeMetric(name='GraphQL/all', scope='',
                duration=self.duration, exclusive=self.exclusive)

        yield TimeMetric(name='GraphQL/%s/all' % product, scope='',
                duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebTransaction':
            yield TimeMetric(name='GraphQL/allWeb', scope='',
                    duration=self.duration, exclusive=self.exclusive)

            yield TimeMetric(name='GraphQL/%s/allWeb' % product, scope='',
                    duration=self.duration, exclusive=self.exclusive)
        else:
            yield TimeMetric(name='GraphQL/allOther', scope='',
                    duration=self.duration, exclusive=self.exclusive)

            yield TimeMetric(name='GraphQL/%s/allOther' % product, scope='',
                    duration=self.duration, exclusive=self.exclusive)

        # Unscoped operation metric

        yield TimeMetric(name=operation_metric_name, scope='',
                duration=self.duration, exclusive=self.exclusive)

        # Now for the children

        for child in self.children:
            for metric in child.time_metrics(stats, root, self):
                yield metric