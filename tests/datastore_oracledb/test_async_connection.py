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

import oracledb
import pytest
from testing_support.db_settings import oracledb_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

ORACLEDB_VERSION = get_package_version_tuple("oracledb")
if ORACLEDB_VERSION < (2,):
    pytest.skip(reason="OracleDB version does not contain async APIs.", allow_module_level=True)

DB_SETTINGS = oracledb_settings()[0]
TABLE_NAME = DB_SETTINGS["table_name"]
PROCEDURE_NAME = DB_SETTINGS["procedure_name"]

HOST = instance_hostname(DB_SETTINGS["host"])
PORT = DB_SETTINGS["port"]


async def execute_db_calls_with_cursor(cursor):
    await cursor.execute(f"""drop table if exists {TABLE_NAME}""")

    await cursor.execute(f"create table {TABLE_NAME} (a INT, b BINARY_FLOAT, c VARCHAR2(10) )")

    await cursor.executemany(
        f"insert into {TABLE_NAME} values (:1, :2, :3)", [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")]
    )

    await cursor.execute(f"""select * from {TABLE_NAME}""")

    async for _row in cursor:
        pass

    await cursor.execute(f"update {TABLE_NAME} set a=:1, b=:2, c=:3 where a=:4", (4, 4.0, "4.0", 1))

    await cursor.execute(f"""delete from {TABLE_NAME} where a=2""")

    await cursor.execute(f"""drop procedure if exists {PROCEDURE_NAME}""")
    await cursor.execute(
        f"""CREATE PROCEDURE {PROCEDURE_NAME} (hello OUT VARCHAR2) AS
                BEGIN
                    hello := 'Hello World!';
                END;
        """
    )
    # Must specify a container for the OUT parameter
    await cursor.callproc(name=PROCEDURE_NAME, parameters=[cursor.var(str)])


_test_execute_scoped_metrics = [
    ("Function/oracledb.connection:connect_async", 1),
    (f"Datastore/statement/Oracle/{TABLE_NAME}/select", 1),
    (f"Datastore/statement/Oracle/{TABLE_NAME}/insert", 1),
    (f"Datastore/statement/Oracle/{TABLE_NAME}/update", 1),
    (f"Datastore/statement/Oracle/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/Oracle/drop", 2),
    ("Datastore/operation/Oracle/create", 2),
    (f"Datastore/statement/Oracle/{PROCEDURE_NAME}/call", 1),
    ("Datastore/operation/Oracle/commit", 2),
    ("Datastore/operation/Oracle/rollback", 1),
]

_test_execute_rollup_metrics = [
    ("Datastore/all", 13),
    ("Datastore/allOther", 13),
    ("Datastore/Oracle/all", 13),
    ("Datastore/Oracle/allOther", 13),
    (f"Datastore/statement/Oracle/{TABLE_NAME}/select", 1),
    (f"Datastore/statement/Oracle/{TABLE_NAME}/insert", 1),
    (f"Datastore/statement/Oracle/{TABLE_NAME}/update", 1),
    (f"Datastore/statement/Oracle/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/Oracle/select", 1),
    ("Datastore/operation/Oracle/insert", 1),
    ("Datastore/operation/Oracle/update", 1),
    ("Datastore/operation/Oracle/delete", 1),
    (f"Datastore/statement/Oracle/{PROCEDURE_NAME}/call", 1),
    ("Datastore/operation/Oracle/call", 1),
    ("Datastore/operation/Oracle/drop", 2),
    ("Datastore/operation/Oracle/create", 2),
    ("Datastore/operation/Oracle/commit", 2),
    ("Datastore/operation/Oracle/rollback", 1),
    (f"Datastore/instance/Oracle/{HOST}/{PORT}", 12),
]


@validate_transaction_metrics(
    "test_async_connection:test_execute_via_async_connection_aenter",
    scoped_metrics=_test_execute_scoped_metrics,
    rollup_metrics=_test_execute_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_async_connection_aenter(loop):
    async def _test():
        connection = oracledb.connect_async(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
            service_name=DB_SETTINGS["service_name"],
        )

        # Use async with and don't await connection directly
        async with connection:
            async with connection.cursor() as cursor:
                await execute_db_calls_with_cursor(cursor)

            await connection.commit()
            await connection.rollback()
            await connection.commit()

    loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_async_connection:test_execute_via_async_connection_await",
    scoped_metrics=_test_execute_scoped_metrics,
    rollup_metrics=_test_execute_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_async_connection_await(loop):
    async def _test():
        connection = oracledb.connect_async(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
            service_name=DB_SETTINGS["service_name"],
        )

        # Await connection instead of using async with
        connection = await connection
        async with connection.cursor() as cursor:
            await execute_db_calls_with_cursor(cursor)

            await connection.commit()
            await connection.rollback()
            await connection.commit()

    loop.run_until_complete(_test())
