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

from flask import Flask
from sanic import Sanic
import json
import webtest

from testing_support.asgi_testing import AsgiTest
from framework_graphql._target_application import _target_application as schema
from graphql_server.flask import GraphQLView as FlaskView
from graphql_server.sanic import GraphQLView as SanicView

# Sanic
target_application = dict()

sanic_app = Sanic(name="SanicGraphQL")
routes = [
    sanic_app.add_route(SanicView.as_view(schema=schema), "/graphql"),
]
sanic_app = AsgiTest(sanic_app)

def sanic_execute(query):
    response = sanic_app.make_request(
        "POST", "/graphql", body=json.dumps({"query": query}), headers={"Content-Type": "application/json"}
    )
    body = json.loads(response.body.decode("utf-8"))
    
    if not isinstance(query, str) or "error" in query:
        try:
            assert response.status != 200
        except AssertionError:
            assert body["errors"]
    else:
        assert response.status == 200
        assert "errors" not in body or not body["errors"]

    return response

target_application["Sanic"] = sanic_execute

# Flask

flask_app = Flask("FlaskGraphQL")
flask_app.add_url_rule("/graphql", view_func=FlaskView.as_view("graphql", schema=schema))
flask_app = webtest.TestApp(flask_app)

def flask_execute(query):
    if not isinstance(query, str) or "error" in query:
        expect_errors = True
    else:
        expect_errors = False

    response = flask_app.post(
        "/graphql", json.dumps({"query": query}), headers={"Content-Type": "application/json"}, expect_errors=expect_errors
    )

    body = json.loads(response.body.decode("utf-8"))
    if expect_errors:
        assert body["errors"]
    else:
        assert "errors" not in body or not body["errors"]

    return response

target_application["Flask"] = flask_execute
