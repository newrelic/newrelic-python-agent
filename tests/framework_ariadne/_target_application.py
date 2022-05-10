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


import asyncio
import json
import pytest

from ._target_schema_sync import target_schema as target_schema_sync, target_asgi_application as target_asgi_application_sync, target_wsgi_application as target_wsgi_application_sync
from ._target_schema_async import target_schema as target_schema_async, target_asgi_application as target_asgi_application_async

from graphql import MiddlewareManager



def check_response(query, success, response):
    if isinstance(query, str) and "error" not in query:
        assert success and not "errors" in response, response["errors"]
        assert response["data"]
    else:
        assert "errors" in response, response


def run_sync(schema):
    def _run_sync(query, middleware=None):
        from ariadne import graphql_sync

        if middleware:
            middleware = MiddlewareManager(*middleware)
        else:
            middleware = None

        success, response = graphql_sync(schema, {"query": query}, middleware=middleware)
        check_response(query, success, response)

        return response.get("data", {})
    return _run_sync


def run_async(schema):
    def _run_async(query, middleware=None):
        from ariadne import graphql

        if middleware:
            middleware = MiddlewareManager(*middleware)
        else:
            middleware = None

        loop = asyncio.get_event_loop()
        success, response = loop.run_until_complete(graphql(schema, {"query": query}, middleware=middleware))
        check_response(query, success, response)

        return response.get("data", {})
    return _run_async


def run_wsgi(app):
    def _run_asgi(query, middleware=None):
        if not isinstance(query, str) or "error" in query:
            expect_errors = True
        else:
            expect_errors = False

        app.app.middleware = middleware

        response = app.post(
            "/", json.dumps({"query": query}), headers={"Content-Type": "application/json"}, expect_errors=expect_errors
        )

        body = json.loads(response.body.decode("utf-8"))
        if expect_errors:
            assert body["errors"]
        else:
            assert "errors" not in body or not body["errors"]

        return body.get("data", {})

    return _run_asgi


def run_asgi(app):
    def _run_asgi(query, middleware=None):
        app.asgi_application.middleware = middleware

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
            assert "errors" not in body or not body["errors"]

        return body.get("data", {})
    return _run_asgi


target_application = {
    "sync-sync": run_sync(target_schema_sync),
    "async-sync": run_async(target_schema_sync),
    "async-async": run_async(target_schema_async),
    "wsgi-sync": run_wsgi(target_wsgi_application_sync),
    "asgi-sync": run_asgi(target_asgi_application_sync),
    "asgi-async": run_asgi(target_asgi_application_async),
}
