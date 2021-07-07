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
import logging

from newrelic.common.async_wrapper import async_wrapper
from newrelic.api.time_trace import TimeTrace, current_trace
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object
from newrelic.core.graphql_node import GraphQLNode
from newrelic.core.stack_trace import current_stack

_logger = logging.getLogger(__name__)


class GraphQLTrace(TimeTrace):
    def __init__(self, **kwargs):
        parent = None
        if kwargs:
            if len(kwargs) > 1:
                raise TypeError("Invalid keyword arguments:", kwargs)
            parent = kwargs['parent']
        super(GraphQLTrace, self).__init__(parent)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict())


    def create_node(self):
        return GraphQLNode(
            children=self.children,
            start_time=self.start_time,
            end_time=self.end_time,
            duration=self.duration,
            exclusive=self.exclusive,
            guid=self.guid,
            agent_attributes=self.agent_attributes,
            user_attributes=self.user_attributes,
        )


class GraphQLResolverTrace(TimeTrace):
    def __init__(self, field_name=None, **kwargs):
        parent = None
        if kwargs:
            if len(kwargs) > 1:
                raise TypeError("Invalid keyword arguments:", kwargs)
            parent = kwargs['parent']
        super(GraphQLResolverTrace, self).__init__(parent)

        self.field_name = field_name


    def create_node(self):
        return GraphQLNode(
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

def GraphQLTraceWrapper(wrapped):
    def _nr_graphql_trace_wrapper_(wrapped, instance, args, kwargs):
        wrapper = async_wrapper(wrapped)
        if not wrapper:
            parent = current_trace()
            if not parent:
                return wrapped(*args, **kwargs)
        else:
            parent = None

        trace = GraphQLTrace(parent=parent)

        if wrapper:
            return wrapper(wrapped, trace)(*args, **kwargs)

        with trace:
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, _nr_graphql_trace_wrapper_)


def graphql_trace():
    return functools.partial(GraphQLTraceWrapper)

def wrap_graphql_trace(module, object_path):
    wrap_object(module, object_path, GraphQLTraceWrapper)
