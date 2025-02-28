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

import os

import psycopg
from conftest import maybe_await
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@validate_transaction_metrics("test_register:test_register_json", background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_register_json(loop, connection):
    def test():
        cursor = connection.cursor()

        psycopg.types.json.set_json_loads(loads=lambda x: x, context=connection)
        psycopg.types.json.set_json_loads(loads=lambda x: x, context=cursor)

    if hasattr(connection, "__aenter__"):

        async def coro():
            async with connection:
                test()

        loop.run_until_complete(coro())
    else:
        with connection:
            test()


@validate_transaction_metrics("test_register:test_register_range", background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_register_range(loop, connection):
    async def test():
        type_name = f"floatrange_{str(os.getpid())}"

        create_sql = f"CREATE TYPE {type_name} AS RANGE (subtype = float8,subtype_diff = float8mi)"

        cursor = connection.cursor()

        await maybe_await(cursor.execute(f"DROP TYPE if exists {type_name}"))
        await maybe_await(cursor.execute(create_sql))

        range_type_info = await maybe_await(psycopg.types.range.RangeInfo.fetch(connection, type_name))
        range_type_info.register(connection)

        await maybe_await(cursor.execute(f"DROP TYPE if exists {type_name}"))
        await maybe_await(cursor.execute(create_sql))

        range_type_info = await maybe_await(psycopg.types.range.RangeInfo.fetch(connection, type_name))
        range_type_info.register(cursor)

        await maybe_await(cursor.execute(f"DROP TYPE if exists {type_name}"))

    if hasattr(connection, "__aenter__"):

        async def coro():
            async with connection:
                await test()

        loop.run_until_complete(coro())
    else:
        with connection:
            loop.run_until_complete(test())
