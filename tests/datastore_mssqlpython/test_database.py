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

import pytest
from conftest import DB_SETTINGS
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@pytest.fixture(scope="session")
def mssql_python():
    """Delay package import to execution time rather than import time."""
    import mssql_python
    return mssql_python


DB_NAMESPACE = DB_SETTINGS["namespace"]
TABLE_NAME = f"datastore_mssqlpython_{DB_NAMESPACE}"
PROCEDURE_NAME = f"hello_{DB_NAMESPACE}"

_test_scoped_metrics = [
    ("Function/mssql_python.db_connection:connect", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/select", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/insert", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/update", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/MSSQL/drop", 2),
    ("Datastore/operation/MSSQL/create", 2),
    ("Datastore/operation/MSSQL/commit", 2),
    ("Datastore/operation/MSSQL/rollback", 1),
]

_test_rollup_metrics = [
    ("Datastore/all", 12),
    ("Datastore/allOther", 12),
    ("Datastore/MSSQL/all", 12),
    ("Datastore/MSSQL/allOther", 12),
    ("Datastore/operation/MSSQL/select", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/select", 1),
    ("Datastore/operation/MSSQL/insert", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/insert", 1),
    ("Datastore/operation/MSSQL/update", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/update", 1),
    ("Datastore/operation/MSSQL/delete", 1),
    (f"Datastore/statement/MSSQL/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/MSSQL/drop", 2),
    ("Datastore/operation/MSSQL/create", 2),
    ("Datastore/operation/MSSQL/commit", 2),
    ("Datastore/operation/MSSQL/rollback", 1),
    (f"Datastore/instance/MSSQL/{instance_hostname(DB_SETTINGS['host'])}/{DB_SETTINGS['port']}", 11),
]


@validate_transaction_metrics(
    "test_database:test_execute",
    scoped_metrics=_test_scoped_metrics,
    rollup_metrics=_test_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=dict)
@background_task()
def test_execute(version, mssql_python, connection_string):
    assert version is not None

    connection = mssql_python.connect(connection_string)

    cursor = connection.cursor()

    cursor.execute(f"drop table if exists {TABLE_NAME}")

    cursor.execute(f"create table {TABLE_NAME} (a integer, b real, c text)")

    cursor.executemany(
        f"insert into {TABLE_NAME} values (%(a)s, %(b)s, %(c)s)",
        [{"a": 1, "b": 1.0, "c": "1.0"}, {"a": 2, "b": 2.2, "c": "2.2"}, {"a": 3, "b": 3.3, "c": "3.3"}],
    )

    cursor.execute(f"select * from {TABLE_NAME}")

    for _row in cursor:
        pass

    cursor.execute(
        f"update {TABLE_NAME} set a=%(a)s, b=%(b)s, c=%(c)s where a=%(old_a)s",
        {"a": 4, "b": 4.0, "c": "4.0", "old_a": 1},
    )

    cursor.execute(f"delete from {TABLE_NAME} where a=2")

    cursor.execute(f"drop procedure if exists {PROCEDURE_NAME}")
    cursor.execute(
        f"""CREATE PROCEDURE {PROCEDURE_NAME}
                      AS BEGIN
                        SELECT 'Hello World!'
                      END"""
    )

    connection.commit()
    connection.rollback()
    connection.commit()


@validate_transaction_metrics(
    "test_database:test_execute_via_context_manager",
    scoped_metrics=_test_scoped_metrics,
    rollup_metrics=_test_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=dict)
@background_task()
def test_execute_via_context_manager(version, mssql_python, connection_string):
    assert version is not None

    with mssql_python.connect(connection_string) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"drop table if exists {TABLE_NAME}")

            cursor.execute(f"create table {TABLE_NAME} (a integer, b real, c text)")

            cursor.executemany(
                f"insert into {TABLE_NAME} values (%(a)s, %(b)s, %(c)s)",
                [{"a": 1, "b": 1.0, "c": "1.0"}, {"a": 2, "b": 2.2, "c": "2.2"}, {"a": 3, "b": 3.3, "c": "3.3"}],
            )

            cursor.execute(f"select * from {TABLE_NAME}")

            for _row in cursor:
                pass

            cursor.execute(
                f"update {TABLE_NAME} set a=%(a)s, b=%(b)s, c=%(c)s where a=%(old_a)s",
                {"a": 4, "b": 4.0, "c": "4.0", "old_a": 1},
            )

            cursor.execute(f"delete from {TABLE_NAME} where a=2")

            cursor.execute(f"drop procedure if exists {PROCEDURE_NAME}")
            cursor.execute(
                f"""CREATE PROCEDURE {PROCEDURE_NAME}
                            AS BEGIN
                                SELECT 'Hello World!'
                            END"""
            )

        connection.commit()
        connection.rollback()
        connection.commit()
