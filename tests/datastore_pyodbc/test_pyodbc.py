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
from testing_support.db_settings import postgresql_settings
from testing_support.validators.validate_database_trace_inputs import (
    validate_database_trace_inputs,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

DB_SETTINGS = postgresql_settings()[0]


@validate_transaction_metrics(
    "test_pyodbc:test_execute_via_cursor",
    scoped_metrics=[
        ("Function/pyodbc:connect", 1),
    ],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/ODBC/all", 1),
        ("Datastore/ODBC/allOther", 1),
    ],
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor(pyodbc_driver):
    import pyodbc

    with pyodbc.connect(
        "DRIVER={%s};SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s"
        % (
            pyodbc_driver,
            DB_SETTINGS["host"],
            DB_SETTINGS["port"],
            DB_SETTINGS["name"],
            DB_SETTINGS["user"],
            DB_SETTINGS["password"],
        )
    ) as connection:
        cursor = connection.cursor()
        cursor.execute("""drop table if exists %s""" % DB_SETTINGS["table_name"])
        cursor.execute("""create table %s """ % DB_SETTINGS["table_name"] + """(a integer, b real, c text)""")
        cursor.executemany(
            """insert into %s """ % DB_SETTINGS["table_name"] + """values (?, ?, ?)""",
            [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")],
        )
        cursor.execute("""select * from %s""" % DB_SETTINGS["table_name"])
        for row in cursor:
            pass
        cursor.execute(
            """update %s """ % DB_SETTINGS["table_name"] + """set a=?, b=?, c=? where a=?""",
            (4, 4.0, "4.0", 1),
        )
        cursor.execute("""delete from %s where a=2""" % DB_SETTINGS["table_name"])
        connection.commit()

        cursor.execute("SELECT now()")
        cursor.execute("SELECT pg_sleep(0.25)")

        connection.rollback()
        connection.commit()


@validate_transaction_metrics(
    "test_pyodbc:test_rollback_on_exception",
    scoped_metrics=[
        ("Function/pyodbc:connect", 1),
    ],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/ODBC/all", 1),
        ("Datastore/ODBC/allOther", 1),
    ],
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception(pyodbc_driver):
    import pyodbc

    with pytest.raises(RuntimeError):
        with pyodbc.connect(
            "DRIVER={%s};SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s"
            % (
                pyodbc_driver,
                DB_SETTINGS["host"],
                DB_SETTINGS["port"],
                DB_SETTINGS["name"],
                DB_SETTINGS["user"],
                DB_SETTINGS["password"],
            )
        ) as connection:
            raise RuntimeError("error")


@pytest.fixture
def pyodbc_driver():
    import pyodbc

    driver_name = "PostgreSQL Unicode"
    assert driver_name in pyodbc.drivers()
    return driver_name
