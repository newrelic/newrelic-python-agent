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

import sys

from newrelic.api.database_trace import register_database_client
from newrelic.api.function_trace import FunctionTrace
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper, wrap_object
from newrelic.hooks.database_dbapi2_async import AsyncConnectionFactory as DBAPI2AsyncConnectionFactory
from newrelic.hooks.database_dbapi2_async import AsyncConnectionWrapper as DBAPI2AsyncConnectionWrapper
from newrelic.hooks.database_dbapi2_async import AsyncCursorWrapper as DBAPI2AsyncCursorWrapper


class AsyncCursorContextManagerWrapper(ObjectProxy):
    __cursor_wrapper__ = DBAPI2AsyncCursorWrapper

    def __init__(self, context_manager, dbapi2_module, connect_params, cursor_args):
        super().__init__(context_manager)
        self._nr_dbapi2_module = dbapi2_module
        self._nr_connect_params = connect_params
        self._nr_cursor_args = cursor_args

    async def __aenter__(self):
        cursor = await self.__wrapped__.__aenter__()
        return self.__cursor_wrapper__(cursor, self._nr_dbapi2_module, self._nr_connect_params, self._nr_cursor_args)

    async def __aexit__(self, exc, val, tb):
        return await self.__wrapped__.__aexit__(exc, val, tb)

    def __await__(self):
        # Handle bidirectional generator protocol using code from generator_wrapper
        g = self.__wrapped__.__await__()
        try:
            yielded = g.send(None)
            while True:
                try:
                    sent = yield yielded
                except GeneratorExit:
                    g.close()
                    raise
                except BaseException as e:
                    yielded = g.throw(e)
                else:
                    yielded = g.send(sent)
        except StopIteration as e:
            # Catch the StopIteration and wrap the return value.
            cursor = e.value
            wrapped_cursor = self.__cursor_wrapper__(
                cursor, self._nr_dbapi2_module, self._nr_connect_params, self._nr_cursor_args
            )
            return wrapped_cursor  # Return here instead of raising StopIteration to properly follow generator protocol


class AsyncConnectionWrapper(DBAPI2AsyncConnectionWrapper):
    __cursor_wrapper__ = AsyncCursorContextManagerWrapper


class AsyncConnectionFactory(DBAPI2AsyncConnectionFactory):
    __connection_wrapper__ = AsyncConnectionWrapper


def wrap_pool__acquire(dbapi2_module):
    async def _wrap_pool__acquire(wrapped, instance, args, kwargs):
        rollup = ["Datastore/all", f"Datastore/{dbapi2_module._nr_database_product}/all"]

        with FunctionTrace(name=callable_name(wrapped), terminal=True, rollup=rollup, source=wrapped):
            connection = await wrapped(*args, **kwargs)
            connection_kwargs = getattr(instance, "_conn_kwargs", {})
            return AsyncConnectionWrapper(connection, dbapi2_module, (((), connection_kwargs)))

    return _wrap_pool__acquire


def instance_info(args, kwargs):
    def _bind_params(host=None, user=None, password=None, db=None, port=None, *args, **kwargs):
        return host, port, db

    host, port, db = _bind_params(*args, **kwargs)

    return (host, port, db)


def instrument_aiomysql(module):
    register_database_client(
        module,
        database_product="MySQL",
        quoting_style="single+double",
        explain_query="explain",
        explain_stmts=("select",),
        instance_info=instance_info,
    )

    # Only instrument the connect method directly, don't instrument
    # Connection. This follows the DBAPI2 spec and what was done for
    # PyMySQL which this library is based on.

    wrap_object(module, "connect", AsyncConnectionFactory, (module,))


def instrument_aiomysql_pool(module):
    dbapi2_module = sys.modules["aiomysql"]
    if hasattr(module, "Pool"):
        if hasattr(module.Pool, "_acquire"):
            wrap_function_wrapper(module, "Pool._acquire", wrap_pool__acquire(dbapi2_module))
