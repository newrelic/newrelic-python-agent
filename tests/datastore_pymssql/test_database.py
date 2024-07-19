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

from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs

from testing_support.db_settings import mssql_settings

from newrelic.api.background_task import background_task

DB_SETTINGS = mssql_settings()[0]
TABLE_NAME = "datastore_pymssql_" + DB_SETTINGS["namespace"]
PROCEDURE_NAME = "hello_" + DB_SETTINGS["namespace"]


def execute_db_calls_with_cursor(cursor):
    cursor.execute("""drop table if exists %s""" % TABLE_NAME)

    cursor.execute("""create table %s """ % TABLE_NAME + """(a integer, b real, c text)""")

    cursor.executemany(
        """insert into %s """ % TABLE_NAME + """values (%s, %s, %s)""",
        [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")],
    )

    cursor.execute("""select * from %s""" % TABLE_NAME)

    for row in cursor:
        pass

    cursor.execute("""update %s""" % TABLE_NAME + """ set a=%s, b=%s, """ """c=%s where a=%s""", (4, 4.0, "4.0", 1))

    cursor.execute("""delete from %s where a=2""" % TABLE_NAME)
    cursor.execute("""drop procedure if exists %s""" % PROCEDURE_NAME)
    cursor.execute(
        """CREATE PROCEDURE %s AS
                      BEGIN
                        SELECT 'Hello World!';
                      END"""
        % PROCEDURE_NAME
    )

    cursor.callproc(PROCEDURE_NAME)


_test_scoped_metrics = [
    ("Function/pymssql._pymssql:connect", 1),
    ("Datastore/statement/MSSQL/%s/select" % TABLE_NAME, 1),
    ("Datastore/statement/MSSQL/%s/insert" % TABLE_NAME, 1),
    ("Datastore/statement/MSSQL/%s/update" % TABLE_NAME, 1),
    ("Datastore/statement/MSSQL/%s/delete" % TABLE_NAME, 1),
    ("Datastore/operation/MSSQL/drop", 2),
    ("Datastore/operation/MSSQL/create", 2),
    ("Datastore/statement/MSSQL/%s/call" % PROCEDURE_NAME, 1),
    ("Datastore/operation/MSSQL/commit", 2),
    ("Datastore/operation/MSSQL/rollback", 1),
]

_test_rollup_metrics = [
    ("Datastore/all", 13),
    ("Datastore/allOther", 13),
    ("Datastore/MSSQL/all", 13),
    ("Datastore/MSSQL/allOther", 13),
    ("Datastore/statement/MSSQL/%s/select" % TABLE_NAME, 1),
    ("Datastore/statement/MSSQL/%s/insert" % TABLE_NAME, 1),
    ("Datastore/statement/MSSQL/%s/update" % TABLE_NAME, 1),
    ("Datastore/statement/MSSQL/%s/delete" % TABLE_NAME, 1),
    ("Datastore/operation/MSSQL/select", 1),
    ("Datastore/operation/MSSQL/insert", 1),
    ("Datastore/operation/MSSQL/update", 1),
    ("Datastore/operation/MSSQL/delete", 1),
    ("Datastore/statement/MSSQL/%s/call" % PROCEDURE_NAME, 1),
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
