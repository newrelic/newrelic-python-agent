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

from ._target_schema_sync import target_schema as target_schema_sync, target_asgi_application as target_asgi_application_sync
from ._target_schema_async import target_schema as target_schema_async, target_asgi_application as target_asgi_application_async


def run_sync(schema):
    def _run_sync(query, middleware=None):
        from graphql.language.source import Source

        if middleware is not None:
            pytest.skip("Middleware not supported in Strawberry.")

        response = schema.execute_sync(query)

        if isinstance(query, str) and "error" not in query or isinstance(query, Source) and "error" not in query.body:
            assert not response.errors
        else:
            assert response.errors

        return response.data
    return _run_sync


def run_async(schema):
    def _run_async(query, middleware=None):
        from graphql.language.source import Source

        if middleware is not None:
            pytest.skip("Middleware not supported in Strawberry.")

        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(schema.execute(query))

        if isinstance(query, str) and "error" not in query or isinstance(query, Source) and "error" not in query.body:
            assert not response.errors
        else:
            assert response.errors

        return response.data
    return _run_async


def run_asgi(app):
    def _run_asgi(query, middleware=None):
        if middleware is not None:
            pytest.skip("Middleware not supported in Strawberry.")

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

        return body["data"]
    return _run_asgi


target_application = {
    "sync-sync": run_sync(target_schema_sync),
    "async-sync": run_async(target_schema_sync),
    "asgi-sync": run_asgi(target_asgi_application_sync),
    "async-async": run_async(target_schema_async),
    "asgi-async": run_asgi(target_asgi_application_async),
}
