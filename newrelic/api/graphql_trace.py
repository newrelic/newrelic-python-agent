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

import functools

from newrelic.common.async_wrapper import async_wrapper
from newrelic.api.time_trace import TimeTrace, current_trace
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object
from newrelic.core.graphql_node import GraphQLOperationNode, GraphQLResolverNode

class GraphQLOperationTrace(TimeTrace):
    def __init__(self, **kwargs):
        parent = None
        if kwargs:
            if len(kwargs) > 1:
                raise TypeError("Invalid keyword arguments:", kwargs)
            parent = kwargs['parent']
        super(GraphQLOperationTrace, self).__init__(parent)

        self.operation_name = None
        self.operation_type = None
        self.deepest_path = None

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict())

    def finalize_data(self, *args, **kwargs):
        self._add_agent_attribute("graphql.operation.type", self.operation_type or "<unknown>")
        self._add_agent_attribute("graphql.operation.name", self.operation_name or "<anonymous>")
        self._add_agent_attribute("graphql.operation.deepestPath", self.deepest_path or "<unknown>")

        return super(GraphQLOperationTrace, self).finalize_data(*args, **kwargs)


    def create_node(self):
        return GraphQLOperationNode(
            children=self.children,
            start_time=self.start_time,
            end_time=self.end_time,
            duration=self.duration,
            exclusive=self.exclusive,
            guid=self.guid,
            agent_attributes=self.agent_attributes,
            user_attributes=self.user_attributes,
            operation_name=self.operation_name,
            operation_type=self.operation_type,
            deepest_path=self.deepest_path,
        )


def GraphQLOperationTraceWrapper(wrapped):
    def _nr_graphql_trace_wrapper_(wrapped, instance, args, kwargs):
        wrapper = async_wrapper(wrapped)
        if not wrapper:
            parent = current_trace()
            if not parent:
                return wrapped(*args, **kwargs)
        else:
            parent = None

        trace = GraphQLOperationTrace(parent=parent)

        if wrapper:
            return wrapper(wrapped, trace)(*args, **kwargs)

        with trace:
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, _nr_graphql_trace_wrapper_)


def graphql_operation_trace():
    return functools.partial(GraphQLOperationTraceWrapper)

def wrap_graphql_operation_trace(module, object_path):
    wrap_object(module, object_path, GraphQLOperationTraceWrapper)


class GraphQLResolverTrace(GraphQLOperationTrace):
    def __init__(self, field_name=None, **kwargs):
        super(GraphQLResolverTrace, self).__init__(**kwargs)
        self.field_name = field_name


    def finalize_data(self, *args, **kwargs):
        self._add_agent_attribute("graphql.field.name", self.field_name)

        return super(GraphQLResolverTrace, self).finalize_data(*args, **kwargs)


    def create_node(self):
        return GraphQLResolverNode(
            field_name=self.field_name,
            children=self.children,
            start_time=self.start_time,
            end_time=self.end_time,
            duration=self.duration,
            exclusive=self.exclusive,
            guid=self.guid,
            agent_attributes=self.agent_attributes,
            user_attributes=self.user_attributes,
        )


def GraphQLResolverTraceWrapper(wrapped):
    def _nr_graphql_trace_wrapper_(wrapped, instance, args, kwargs):
        wrapper = async_wrapper(wrapped)
        if not wrapper:
            parent = current_trace()
            if not parent:
                return wrapped(*args, **kwargs)
        else:
            parent = None

        trace = GraphQLResolverTrace(parent=parent)

        if wrapper:
            return wrapper(wrapped, trace)(*args, **kwargs)

        with trace:
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, _nr_graphql_trace_wrapper_)


def graphql_resolver_trace():
    return functools.partial(GraphQLResolverTraceWrapper)

def wrap_graphql_resolver_trace(module, object_path):
    wrap_object(module, object_path, GraphQLResolverTraceWrapper)
