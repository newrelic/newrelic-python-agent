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

import newrelic.core.attribute as attribute
import newrelic.core.trace_node

from newrelic.common import system_info
from newrelic.core.metric import TimeMetric

from newrelic.core.node_mixin import GenericNodeMixin


_GraphQLNode = namedtuple('_GraphQLNode',
        ['field_name', 'children', 'start_time', 'end_time',
        'duration', 'exclusive', 'guid', 'agent_attributes',
        'user_attributes'])


class GraphQLNode(_GraphQLNode, GenericNodeMixin):

    @property
    def product(self):
        return "GraphQL"

    @property
    def operation(self):
        return "select"


    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        database node as well as all the child nodes.
        """

        field_name = self.field_name
        product = self.product
        operation = self.operation or 'other'

        # Determine the scoped metric
        operation_metric_name = 'GraphQL/operation/%s/%s' % (product,
                operation)

        field_resolver_metric_name = 'GraphQL/resolve/%s/%s' % (product, field_name)

        scoped_metric_name = operation_metric_name

        yield TimeMetric(name=field_resolver_metric_name, scope=root.path, duration=self.duration,
                         exclusive=self.exclusive)

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

        yield TimeMetric(name=field_resolver_metric_name, scope='', duration=self.duration,
                         exclusive=self.exclusive)


    def trace_node(self, stats, root, connections):
        name = root.string_table.cache(self.name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        root.trace_node_count += 1

        children = []

        # Agent attributes
        params = self.get_trace_segment_params(root.settings)

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=None)

    @property
    def name(self):
        product = self.product
        target = "test"
        operation = self.operation or 'other'

        if target:
            name = 'GraphQL/statement/%s/%s/%s' % (product, target,
                    operation)
        else:
            name = 'GraphQL/operation/%s/%s' % (product, operation)

        return name