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

from testing_support.asgi_testing import AsgiTest
from framework_graphql._target_application import _target_application as schema
from graphql_server.sanic import GraphQLView


sanic_app = Sanic(name="SanicGraphQL")
routes = [
    sanic_app.add_route(GraphQLView.as_view(schema=schema), "/graphql"),
]
target_application = AsgiTest(sanic_app)
