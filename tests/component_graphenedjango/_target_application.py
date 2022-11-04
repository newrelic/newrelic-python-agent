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


import json

import webtest

from .asgi import application as asgi_application
from .wsgi import application as wsgi_application
from .urls import set_schema_and_middleware

from framework_graphene._target_schema_sync import target_schema as target_schema_sync

from testing_support.asgi_testing import AsgiTest

def check_response(query, success, response):
    if isinstance(query, str) and "error" not in query:
        assert success and "errors" not in response, response["errors"]
        assert response["data"]
    else:
        assert "errors" in response, response


def run_asgi(app, schema):
    def _run_asgi(query, middleware=None):
        set_schema_and_middleware(schema, middleware)

        response = app.make_request(
            "POST", "/", body=json.dumps({"query": query}), headers={"Content-Type": "application/json"}
        )
        body = json.loads(response.body.decode("utf-8"))

        if not isinstance(query, str) or "error" in query:
            try:
                assert response.status != 200
            except AssertionError:
                assert body["errors"]
        else:
            assert response.status == 200
            assert "errors" not in body or not body["errors"], body["errors"]

        return body.get("data", {})
    return _run_asgi


def run_wsgi(app, schema):
    def _run_wsgi(query, middleware=None):
        set_schema_and_middleware(schema, middleware)

        if not isinstance(query, str) or "error" in query:
            expect_errors = True
        else:
            expect_errors = False

        response = app.post(
            "/", json.dumps({"query": query}), headers={"Content-Type": "application/json"}, expect_errors=expect_errors
        )

        body = json.loads(response.body.decode("utf-8"))
        if expect_errors:
            assert body["errors"]
        else:
            assert "errors" not in body or not body["errors"], body["errors"]

        return body.get("data", {})

    return _run_wsgi


target_application = {
    "wsgi-sync": run_wsgi(webtest.TestApp(wsgi_application), target_schema_sync),
    "asgi-sync": run_asgi(AsgiTest(asgi_application), target_schema_sync),
}
