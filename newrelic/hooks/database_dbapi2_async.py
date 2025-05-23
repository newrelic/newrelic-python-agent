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

from newrelic.api.database_trace import DatabaseTrace, register_database_client
from newrelic.api.function_trace import FunctionTrace
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import ObjectProxy, wrap_object
from newrelic.hooks.database_dbapi2 import DEFAULT


class AsyncCursorWrapper(ObjectProxy):
    def __init__(self, cursor, dbapi2_module, connect_params, cursor_params):
        super().__init__(cursor)
        self._nr_dbapi2_module = dbapi2_module
        self._nr_connect_params = connect_params
        self._nr_cursor_params = cursor_params

    async def execute(self, sql, parameters=DEFAULT, *args, **kwargs):
        if parameters is not DEFAULT:
            with DatabaseTrace(
                sql=sql,
                dbapi2_module=self._nr_dbapi2_module,
                connect_params=self._nr_connect_params,
                cursor_params=self._nr_cursor_params,
                sql_parameters=parameters,
                execute_params=(args, kwargs),
                source=self.__wrapped__.execute,
            ):
                return await self.__wrapped__.execute(sql, parameters, *args, **kwargs)
        else:
            with DatabaseTrace(
                sql=sql,
                dbapi2_module=self._nr_dbapi2_module,
                connect_params=self._nr_connect_params,
                cursor_params=self._nr_cursor_params,
                execute_params=(args, kwargs),
                source=self.__wrapped__.execute,
            ):
                return await self.__wrapped__.execute(sql, **kwargs)

    async def executemany(self, sql, seq_of_parameters, *args, **kwargs):
        try:
            seq_of_parameters = list(seq_of_parameters)
            parameters = seq_of_parameters[0]
        except (TypeError, IndexError):
            parameters = DEFAULT

        if parameters is not DEFAULT:
            with DatabaseTrace(
                sql=sql,
                dbapi2_module=self._nr_dbapi2_module,
                connect_params=self._nr_connect_params,
                cursor_params=self._nr_cursor_params,
                sql_parameters=parameters,
                source=self.__wrapped__.executemany,
            ):
                return await self.__wrapped__.executemany(sql, seq_of_parameters, *args, **kwargs)
        else:
            with DatabaseTrace(
                sql=sql,
                dbapi2_module=self._nr_dbapi2_module,
                connect_params=self._nr_connect_params,
                cursor_params=self._nr_cursor_params,
                source=self.__wrapped__.executemany,
            ):
                return await self.__wrapped__.executemany(sql, seq_of_parameters, *args, **kwargs)

    async def callproc(self, procname, parameters=DEFAULT):
        with DatabaseTrace(
            sql=f"CALL {procname}",
            dbapi2_module=self._nr_dbapi2_module,
            connect_params=self._nr_connect_params,
            source=self.__wrapped__.callproc,
        ):
            if parameters is not DEFAULT:
                return await self.__wrapped__.callproc(procname, parameters)
            else:
                return await self.__wrapped__.callproc(procname)

    def __aiter__(self):
        return self.__wrapped__.__aiter__()

    async def __aenter__(self):
        await self.__wrapped__.__aenter__()
        return self

    async def __aexit__(self, exc=None, val=None, tb=None):
        return await self.__wrapped__.__aexit__(exc, val, tb)


class AsyncConnectionWrapper(ObjectProxy):
    __cursor_wrapper__ = AsyncCursorWrapper

    def __init__(self, connection, dbapi2_module, connect_params):
        super().__init__(connection)
        self._nr_dbapi2_module = dbapi2_module
        self._nr_connect_params = connect_params

    def cursor(self, *args, **kwargs):
        return self.__cursor_wrapper__(
            self.__wrapped__.cursor(*args, **kwargs), self._nr_dbapi2_module, self._nr_connect_params, (args, kwargs)
        )

    async def commit(self):
        with DatabaseTrace(
            sql="COMMIT",
            dbapi2_module=self._nr_dbapi2_module,
            connect_params=self._nr_connect_params,
            source=self.__wrapped__.commit,
        ):
            return await self.__wrapped__.commit()

    async def rollback(self):
        with DatabaseTrace(
            sql="ROLLBACK",
            dbapi2_module=self._nr_dbapi2_module,
            connect_params=self._nr_connect_params,
            source=self.__wrapped__.rollback,
        ):
            return await self.__wrapped__.rollback()

    async def __aenter__(self):
        await self.__wrapped__.__aenter__()
        return self

    async def __aexit__(self, exc=None, val=None, tb=None):
        return await self.__wrapped__.__aexit__(exc, val, tb)


class AsyncConnectionFactory(ObjectProxy):
    __connection_wrapper__ = AsyncConnectionWrapper

    def __init__(self, connect, dbapi2_module):
        super().__init__(connect)
        self._nr_dbapi2_module = dbapi2_module

    async def __call__(self, *args, **kwargs):
        rollup = ["Datastore/all", f"Datastore/{self._nr_dbapi2_module._nr_database_product}/all"]

        with FunctionTrace(name=callable_name(self.__wrapped__), terminal=True, rollup=rollup, source=self.__wrapped__):
            connection = await self.__wrapped__(*args, **kwargs)
            return self.__connection_wrapper__(connection, self._nr_dbapi2_module, (args, kwargs))


def instrument(module):
    register_database_client(module, "DBAPI2", "single")

    wrap_object(module, "connect", AsyncConnectionFactory, (module,))
