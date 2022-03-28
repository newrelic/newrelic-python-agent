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

from sanic import Sanic
from graphql_server.sanic import GraphQLView
from testing_support.asgi_testing import AsgiTest

from graphql import GraphQLObjectType, GraphQLString, GraphQLSchema, GraphQLField


def resolve_hello(root, info):
    return "Hello!"

hello_field = GraphQLField(GraphQLString, resolve=resolve_hello)
query = GraphQLObjectType(
    name="Query",
    fields={
        "hello": hello_field,
    },
)

app = Sanic(name="SanicGraphQL")
routes = [
    app.add_route(GraphQLView.as_view(schema=GraphQLSchema(query=query)), "/graphql"),
]

target_application = AsgiTest(app)
