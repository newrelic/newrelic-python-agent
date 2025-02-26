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

import aiomysql
from testing_support.db_settings import mysql_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

DB_SETTINGS = mysql_settings()[0]
TABLE_NAME = f"datastore_aiomysql_{DB_SETTINGS['namespace']}"
PROCEDURE_NAME = f"hello_{DB_SETTINGS['namespace']}"

HOST = instance_hostname(DB_SETTINGS["host"])
PORT = DB_SETTINGS["port"]


async def execute_db_calls_with_cursor(cursor):
    await cursor.execute(f"""drop table if exists {TABLE_NAME}""")

    await cursor.execute(f"create table {TABLE_NAME} (a integer, b real, c text)")

    await cursor.executemany(
        f"insert into {TABLE_NAME} values (%s, %s, %s)", [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")]
    )

    await cursor.execute(f"""select * from {TABLE_NAME}""")

    async for _ in cursor:
        pass

    await cursor.execute(f"update {TABLE_NAME} set a=%s, b=%s, c=%s where a=%s", (4, 4.0, "4.0", 1))

    await cursor.execute(f"""delete from {TABLE_NAME} where a=2""")
    await cursor.execute(f"""drop procedure if exists {PROCEDURE_NAME}""")
    await cursor.execute(
        f"""CREATE PROCEDURE {PROCEDURE_NAME}()
                      BEGIN
                        SELECT 'Hello World!';
                      END"""
    )

    await cursor.callproc(PROCEDURE_NAME)


SCOPED_METRICS = [
    (f"Datastore/statement/MySQL/{TABLE_NAME}/select", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/insert", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/update", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/MySQL/drop", 2),
    ("Datastore/operation/MySQL/create", 2),
    (f"Datastore/statement/MySQL/{PROCEDURE_NAME}/call", 1),
    ("Datastore/operation/MySQL/commit", 2),
    ("Datastore/operation/MySQL/rollback", 1),
]

ROLLUP_METRICS = [
    ("Datastore/all", 13),
    ("Datastore/allOther", 13),
    ("Datastore/MySQL/all", 13),
    ("Datastore/MySQL/allOther", 13),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/select", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/insert", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/update", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/MySQL/select", 1),
    ("Datastore/operation/MySQL/insert", 1),
    ("Datastore/operation/MySQL/update", 1),
    ("Datastore/operation/MySQL/delete", 1),
    (f"Datastore/statement/MySQL/{PROCEDURE_NAME}/call", 1),
    ("Datastore/operation/MySQL/call", 1),
    ("Datastore/operation/MySQL/drop", 2),
    ("Datastore/operation/MySQL/create", 2),
    ("Datastore/operation/MySQL/commit", 2),
    ("Datastore/operation/MySQL/rollback", 1),
    (f"Datastore/instance/MySQL/{HOST}/{PORT}", 12),
]


@validate_transaction_metrics(
    "test_database:test_execute_via_connection",
    scoped_metrics=list(SCOPED_METRICS) + [("Function/aiomysql.connection:connect", 1)],
    rollup_metrics=list(ROLLUP_METRICS) + [("Function/aiomysql.connection:connect", 1)],
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_connection(loop):
    async def _test():
        connection = await aiomysql.connect(
            db=DB_SETTINGS["name"],
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
        )

        async with connection:
            async with connection.cursor() as cursor:
                await execute_db_calls_with_cursor(cursor)

            await connection.commit()
            await connection.rollback()
            await connection.commit()

    loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_database:test_execute_via_pool",
    scoped_metrics=list(SCOPED_METRICS) + [("Function/aiomysql.pool:Pool._acquire", 1)],
    rollup_metrics=list(ROLLUP_METRICS) + [("Function/aiomysql.pool:Pool._acquire", 1)],
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_pool(loop):
    async def _test():
        pool = await aiomysql.create_pool(
            db=DB_SETTINGS["name"],
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
            loop=loop,
        )
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await execute_db_calls_with_cursor(cursor)

            await connection.commit()
            await connection.rollback()
            await connection.commit()

        pool.close()
        await pool.wait_closed()

    loop.run_until_complete(_test())
