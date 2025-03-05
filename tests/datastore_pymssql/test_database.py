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

import pymssql
from testing_support.db_settings import mssql_settings
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

DB_SETTINGS = mssql_settings()[0]
TABLE_NAME = f"datastore_pymssql_{DB_SETTINGS['namespace']}"
PROCEDURE_NAME = f"hello_{DB_SETTINGS['namespace']}"


def execute_db_calls_with_cursor(cursor):
    cursor.execute(f"""drop table if exists {TABLE_NAME}""")

    cursor.execute(f"create table {TABLE_NAME} (a integer, b real, c text)")

    cursor.executemany(
        f"insert into {TABLE_NAME} values (%s, %s, %s)", [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")]
    )

    cursor.execute(f"""select * from {TABLE_NAME}""")

    for row in cursor:
        pass

    cursor.execute(f"update {TABLE_NAME} set a=%s, b=%s, c=%s where a=%s", (4, 4.0, "4.0", 1))

    cursor.execute(f"""delete from {TABLE_NAME} where a=2""")
    cursor.execute(f"""drop procedure if exists {PROCEDURE_NAME}""")
    cursor.execute(
        f"""CREATE PROCEDURE {PROCEDURE_NAME} AS
                      BEGIN
                        SELECT 'Hello World!';
                      END"""
    )

    cursor.callproc(PROCEDURE_NAME)


_test_scoped_metrics = [
    ("Function/pymssql._pymssql:connect", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/select", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/insert", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/update", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/MSSQL/drop", 2),
    ("Datastore/operation/MSSQL/create", 2),
    (f"Datastore/statement/MSSQL/{PROCEDURE_NAME}/call", 1),
    ("Datastore/operation/MSSQL/commit", 2),
    ("Datastore/operation/MSSQL/rollback", 1),
]

_test_rollup_metrics = [
    ("Datastore/all", 13),
    ("Datastore/allOther", 13),
    ("Datastore/MSSQL/all", 13),
    ("Datastore/MSSQL/allOther", 13),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/select", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/insert", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/update", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/MSSQL/select", 1),
    ("Datastore/operation/MSSQL/insert", 1),
    ("Datastore/operation/MSSQL/update", 1),
    ("Datastore/operation/MSSQL/delete", 1),
    (f"Datastore/statement/MSSQL/{PROCEDURE_NAME}/call", 1),
    ("Datastore/operation/MSSQL/call", 1),
    ("Datastore/operation/MSSQL/drop", 2),
    ("Datastore/operation/MSSQL/create", 2),
    ("Datastore/operation/MSSQL/commit", 2),
    ("Datastore/operation/MSSQL/rollback", 1),
]


@validate_transaction_metrics(
    "test_database:test_execute_via_cursor_context_manager",
    scoped_metrics=_test_scoped_metrics,
    rollup_metrics=_test_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_context_manager():
    connection = pymssql.connect(
        user=DB_SETTINGS["user"], password=DB_SETTINGS["password"], host=DB_SETTINGS["host"], port=DB_SETTINGS["port"]
    )

    with connection:
        cursor = connection.cursor()

        with cursor:
            execute_db_calls_with_cursor(cursor)

        connection.commit()
        connection.rollback()
        connection.commit()
