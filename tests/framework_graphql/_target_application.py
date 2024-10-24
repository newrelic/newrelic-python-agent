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

from graphql.language.source import Source

from ._target_schema_async import target_schema as target_schema_async
from ._target_schema_sync import target_schema as target_schema_sync


def check_response(query, response):
    if isinstance(query, str) and "error" not in query or isinstance(query, Source) and "error" not in query.body:
        assert not response.errors, response.errors
        assert response.data
    else:
        assert response.errors


def run_sync(schema):
    def _run_sync(query, middleware=None):
        try:
            from graphql import graphql_sync as graphql
        except ImportError:
            from graphql import graphql

        response = graphql(schema, query, middleware=middleware)

        check_response(query, response)

        return response.data

    return _run_sync


def run_async(schema):
    import asyncio

    from graphql import graphql

    def _run_async(query, middleware=None):
        coro = graphql(schema, query, middleware=middleware)
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(coro)

        check_response(query, response)

        return response.data

    return _run_async


target_application = {
    "sync-sync": run_sync(target_schema_sync),
    "async-sync": run_async(target_schema_sync),
    "async-async": run_async(target_schema_async),
}
