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

from newrelic.api.database_trace import register_database_client
from newrelic.common.object_wrapper import wrap_object
from newrelic.hooks.database_dbapi2 import ConnectionFactory as DBAPI2ConnectionFactory
from newrelic.hooks.database_dbapi2 import ConnectionWrapper as DBAPI2ConnectionWrapper
from newrelic.hooks.database_dbapi2 import CursorWrapper as DBAPI2CursorWrapper
from newrelic.hooks.database_dbapi2_async import AsyncConnectionFactory as DBAPI2AsyncConnectionFactory
from newrelic.hooks.database_dbapi2_async import AsyncConnectionWrapper as DBAPI2AsyncConnectionWrapper
from newrelic.hooks.database_dbapi2_async import AsyncCursorWrapper as DBAPI2AsyncCursorWrapper


class CursorWrapper(DBAPI2CursorWrapper):
    def __enter__(self):
        self.__wrapped__.__enter__()
        return self


class ConnectionWrapper(DBAPI2ConnectionWrapper):
    __cursor_wrapper__ = CursorWrapper

    def __enter__(self):
        self.__wrapped__.__enter__()
        return self


class ConnectionFactory(DBAPI2ConnectionFactory):
    __connection_wrapper__ = ConnectionWrapper


class AsyncCursorWrapper(DBAPI2AsyncCursorWrapper):
    async def __aenter__(self):
        await self.__wrapped__.__aenter__()
        return self


class AsyncConnectionWrapper(DBAPI2AsyncConnectionWrapper):
    __cursor_wrapper__ = AsyncCursorWrapper

    async def __aenter__(self):
        await self.__wrapped__.__aenter__()
        return self

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
            # Catch the StopIteration and return the wrapped connection instead of the unwrapped.
            if e.value is self.__wrapped__:
                connection = self
            else:
                connection = e.value

            # Return here instead of raising StopIteration to properly follow generator protocol
            return connection


class AsyncConnectionFactory(DBAPI2AsyncConnectionFactory):
    __connection_wrapper__ = AsyncConnectionWrapper

    # Use the synchronous __call__ method as connection_async() is synchronous in oracledb.
    __call__ = DBAPI2ConnectionFactory.__call__


def instance_info(args, kwargs):
    from oracledb import ConnectParams

    dsn = args[0] if args else None

    host = None
    port = None
    service_name = None

    params_from_kwarg = kwargs.pop("params", None)

    params_from_dsn = None
    if dsn:
        try:
            params_from_dsn = ConnectParams()
            if "@" in dsn:
                _, _, connect_string = params_from_dsn.parse_dsn_with_credentials(dsn)
            else:
                connect_string = dsn
            params_from_dsn.parse_connect_string(connect_string)
        except Exception:
            params_from_dsn = None

    host = (
        getattr(params_from_kwarg, "host", None)
        or kwargs.get("host", None)
        or getattr(params_from_dsn, "host", None)
        or "unknown"
    )
    port = str(
        getattr(params_from_kwarg, "port", None)
        or kwargs.get("port", None)
        or getattr(params_from_dsn, "port", None)
        or "1521"
    )
    service_name = (
        getattr(params_from_kwarg, "service_name", None)
        or kwargs.get("service_name", None)
        or getattr(params_from_dsn, "service_name", None)
        or "unknown"
    )

    return host, port, service_name


def instrument_oracledb(module):
    register_database_client(
        module, database_product="Oracle", quoting_style="single+oracle", instance_info=instance_info
    )

    if hasattr(module, "connect"):
        wrap_object(module, "connect", ConnectionFactory, (module,))

    if hasattr(module, "connect_async"):
        wrap_object(module, "connect_async", AsyncConnectionFactory, (module,))
