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

from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, GraphQLString


def resolve_hello(root, info):
    return "Hello!"


try:
    hello_field = GraphQLField(GraphQLString, resolver=resolve_hello)
except TypeError:
    hello_field = GraphQLField(GraphQLString, resolve=resolve_hello)

query = GraphQLObjectType(name="Hello", fields={"hello": hello_field})

_target_application = GraphQLSchema(query=query)
