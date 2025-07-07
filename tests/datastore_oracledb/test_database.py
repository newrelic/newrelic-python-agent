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
from testing_support.db_settings import oracledb_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

DB_SETTINGS = oracledb_settings()[0]
TABLE_NAME = DB_SETTINGS["table_name"]
PROCEDURE_NAME = DB_SETTINGS["procedure_name"]

HOST = instance_hostname(DB_SETTINGS["host"])
PORT = DB_SETTINGS["port"]


def execute_db_calls_with_cursor(cursor):
    cursor.execute(f"""drop table if exists {TABLE_NAME}""")

    cursor.execute(f"create table {TABLE_NAME} (a INT, b BINARY_FLOAT, c VARCHAR2(10) )")

    cursor.executemany(
        f"insert into {TABLE_NAME} values (:1, :2, :3)", [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")]
    )

    cursor.execute(f"""select * from {TABLE_NAME}""")

    for _row in cursor:
        pass

    cursor.execute(f"update {TABLE_NAME} set a=:1, b=:2, c=:3 where a=:4", (4, 4.0, "4.0", 1))

    cursor.execute(f"""delete from {TABLE_NAME} where a=2""")

    cursor.execute(f"""drop procedure if exists {PROCEDURE_NAME}""")
    cursor.execute(
        f"""CREATE PROCEDURE {PROCEDURE_NAME} (hello OUT VARCHAR2) AS
                BEGIN
                    hello := 'Hello World!';
                END;
        """
    )
    cursor.callproc(PROCEDURE_NAME, [cursor.var(str)])  # Must specify a container for the OUT parameter


_test_execute_via_cursor_scoped_metrics = [
    ("Function/oracledb.connection:connect", 1),
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

_test_execute_via_cursor_rollup_metrics = [
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
    "test_database:test_execute_via_cursor",
    scoped_metrics=_test_execute_via_cursor_scoped_metrics,
    rollup_metrics=_test_execute_via_cursor_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    connection = oracledb.connect(
        user=DB_SETTINGS["user"], password=DB_SETTINGS["password"], host=DB_SETTINGS["host"], port=DB_SETTINGS["port"]
    )

    with connection:
        with connection.cursor() as cursor:
            execute_db_calls_with_cursor(cursor)

        connection.commit()
        connection.rollback()
        connection.commit()
