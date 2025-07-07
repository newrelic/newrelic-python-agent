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
from newrelic.hooks.database_dbapi2_async import AsyncConnectionFactory
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


class AsyncConnectionFactory(DBAPI2AsyncConnectionFactory):
    __connection_wrapper__ = AsyncConnectionWrapper


def instance_info(args, kwargs):
    pass


def instrument_oracledb(module):
    register_database_client(module, database_product="Oracle", quoting_style="single+oracle")

    wrap_object(module, "connect", ConnectionFactory, (module,))
    wrap_object(module, "connect_async", AsyncConnectionFactory, (module,))
