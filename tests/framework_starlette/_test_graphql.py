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

from starlette.applications import Starlette
from starlette.routing import Route
from testing_support.asgi_testing import AsgiTest

from graphene import ObjectType, String, Schema
from graphql.execution.executors.asyncio import AsyncioExecutor
from starlette.graphql import GraphQLApp


class Query(ObjectType):
    hello = String()

    def resolve_hello(self, info):
        return "Hello!"


routes = [
    Route("/async", GraphQLApp(executor_class=AsyncioExecutor, schema=Schema(query=Query))),
    Route("/sync", GraphQLApp(schema=Schema(query=Query))),
]

app = Starlette(routes=routes)
target_application = AsgiTest(app)
