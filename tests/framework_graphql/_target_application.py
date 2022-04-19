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

from graphql import __version__ as version
from graphql.language.source import Source

from newrelic.packages import six
from newrelic.hooks.framework_graphql import is_promise

from _target_schema_sync import target_schema as target_schema_sync

try:
    import promise
    from promise.schedulers.asyncio import AsyncioScheduler
    promise.set_default_scheduler(AsyncioScheduler())
except ImportError:
    pass

is_graphql_2 = int(version.split(".")[0]) == 2

def run_sync(schema):
    def _run_sync(query, middleware=None):
        try:
            from graphql import graphql_sync as graphql
        except ImportError:
            from graphql import graphql

        response = graphql(schema, query, middleware=middleware)

        if isinstance(query, str) and "error" not in query or isinstance(query, Source) and "error" not in query.body:
            assert not response.errors, response.errors
        else:
            assert response.errors

        return response.data

    return _run_sync


def run_async(schema):
    def _run_async(query, middleware=None):
        from graphql import graphql
        if is_graphql_2:
            from graphql.execution.executors.asyncio import AsyncioExecutor
            def graphql_run(*args, **kwargs):
                return graphql(*args, executor=AsyncioExecutor(), **kwargs)
                # return graphql(*args, return_promise=True, executor=AsyncioExecutor(), **kwargs)
        else:
            graphql_run = graphql

        coro = graphql_run(schema, query, middleware=middleware)
        response = coro

        if is_promise(coro):
            response = coro.get()
        elif six.PY3:
            import asyncio

            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(coro)
        else:
            raise NotImplementedError()

        if isinstance(query, str) and "error" not in query or isinstance(query, Source) and "error" not in query.body:
            assert not response.errors, response.errors
            assert response.data
        else:
            assert response.errors

        return response.data

    return _run_async


def run_promise(schema):
    def _run_promise(query, middleware=None):
        from graphql import graphql
        if is_graphql_2:
            def graphql_run(*args, **kwargs):
                return graphql(*args, return_promise=True, **kwargs)
        else:
            graphql_run = graphql

        coro = graphql_run(schema, query, middleware=middleware)
        response = coro.get()

        if isinstance(query, str) and "error" not in query or isinstance(query, Source) and "error" not in query.body:
            assert not response.errors, response.errors
            assert response.data
        else:
            assert response.errors

        return response.data

    return _run_promise


target_application = {
    "sync-sync": run_sync(target_schema_sync),
    "async-sync": run_async(target_schema_sync),
}

if is_graphql_2:
    from _target_schema_promise import target_schema as target_schema_promise
    target_application["async-promise"] = run_promise(target_schema_promise)

if six.PY3:
    from _target_schema_async import target_schema as target_schema_async
    target_application["async-async"] = run_async(target_schema_async)
