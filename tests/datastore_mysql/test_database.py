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

import mysql.connector
from testing_support.db_settings import mysql_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

DB_SETTINGS = mysql_settings()
DB_SETTINGS = DB_SETTINGS[0]
DB_NAMESPACE = DB_SETTINGS["namespace"]
DB_PROCEDURE = f"hello_{DB_NAMESPACE}"

mysql_version = get_package_version_tuple("mysql.connector")

if mysql_version >= (8, 0, 30):
    _connector_metric_name = "Function/mysql.connector.pooling:connect"
else:
    _connector_metric_name = "Function/mysql.connector:connect"

_test_execute_via_cursor_scoped_metrics = [
    (_connector_metric_name, 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/select", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/insert", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/update", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/delete", 1),
    ("Datastore/operation/MySQL/drop", 2),
    ("Datastore/operation/MySQL/create", 2),
    (f"Datastore/statement/MySQL/{DB_PROCEDURE}/call", 1),
    ("Datastore/operation/MySQL/commit", 2),
    ("Datastore/operation/MySQL/rollback", 1),
]

_test_execute_via_cursor_rollup_metrics = [
    ("Datastore/all", 13),
    ("Datastore/allOther", 13),
    ("Datastore/MySQL/all", 13),
    ("Datastore/MySQL/allOther", 13),
    ("Datastore/operation/MySQL/select", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/select", 1),
    ("Datastore/operation/MySQL/insert", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/insert", 1),
    ("Datastore/operation/MySQL/update", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/update", 1),
    ("Datastore/operation/MySQL/delete", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/delete", 1),
    (f"Datastore/statement/MySQL/{DB_PROCEDURE}/call", 1),
    ("Datastore/operation/MySQL/call", 1),
    ("Datastore/operation/MySQL/drop", 2),
    ("Datastore/operation/MySQL/create", 2),
    ("Datastore/operation/MySQL/commit", 2),
    ("Datastore/operation/MySQL/rollback", 1),
    (f"Datastore/instance/MySQL/{instance_hostname(DB_SETTINGS['host'])}/{DB_SETTINGS['port']}", 12),
]


@validate_transaction_metrics(
    "test_database:test_execute_via_cursor",
    scoped_metrics=_test_execute_via_cursor_scoped_metrics,
    rollup_metrics=_test_execute_via_cursor_rollup_metrics,
    background_task=True,
)
@validate_transaction_metrics(
    "test_database:test_execute_via_cursor",
    scoped_metrics=_test_execute_via_cursor_scoped_metrics,
    rollup_metrics=_test_execute_via_cursor_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=dict)
@background_task()
def test_execute_via_cursor(table_name):
    assert mysql_version is not None
    connection = mysql.connector.connect(
        db=DB_SETTINGS["name"],
        user=DB_SETTINGS["user"],
        passwd=DB_SETTINGS["password"],
        host=DB_SETTINGS["host"],
        port=DB_SETTINGS["port"],
    )

    cursor = connection.cursor()

    cursor.execute(f"""drop table if exists `{table_name}`""")

    cursor.execute(f"""create table {table_name} (a integer, b real, c text)""")

    cursor.executemany(
        f"insert into `{table_name}` values (%(a)s, %(b)s, %(c)s)",
        [{"a": 1, "b": 1.0, "c": "1.0"}, {"a": 2, "b": 2.2, "c": "2.2"}, {"a": 3, "b": 3.3, "c": "3.3"}],
    )

    cursor.execute(f"""select * from {table_name}""")

    for row in cursor:
        pass

    cursor.execute(
        f"update `{table_name}` set a=%(a)s, b=%(b)s, c=%(c)s where a=%(old_a)s",
        {"a": 4, "b": 4.0, "c": "4.0", "old_a": 1},
    )

    cursor.execute(f"""delete from `{table_name}` where a=2""")

    cursor.execute(f"""drop procedure if exists {DB_PROCEDURE}""")
    cursor.execute(
        f"""CREATE PROCEDURE {DB_PROCEDURE}()
                      BEGIN
                        SELECT 'Hello World!';
                      END"""
    )

    cursor.callproc(f"{DB_PROCEDURE}")

    connection.commit()
    connection.rollback()
    connection.commit()


_test_connect_using_alias_scoped_metrics = [
    (_connector_metric_name, 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/select", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/insert", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/update", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/delete", 1),
    ("Datastore/operation/MySQL/drop", 2),
    ("Datastore/operation/MySQL/create", 2),
    (f"Datastore/statement/MySQL/{DB_PROCEDURE}/call", 1),
    ("Datastore/operation/MySQL/commit", 2),
    ("Datastore/operation/MySQL/rollback", 1),
]

_test_connect_using_alias_rollup_metrics = [
    ("Datastore/all", 13),
    ("Datastore/allOther", 13),
    ("Datastore/MySQL/all", 13),
    ("Datastore/MySQL/allOther", 13),
    ("Datastore/operation/MySQL/select", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/select", 1),
    ("Datastore/operation/MySQL/insert", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/insert", 1),
    ("Datastore/operation/MySQL/update", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/update", 1),
    ("Datastore/operation/MySQL/delete", 1),
    (f"Datastore/statement/MySQL/datastore_mysql_{DB_NAMESPACE}/delete", 1),
    (f"Datastore/statement/MySQL/{DB_PROCEDURE}/call", 1),
    ("Datastore/operation/MySQL/call", 1),
    ("Datastore/operation/MySQL/drop", 2),
    ("Datastore/operation/MySQL/create", 2),
    ("Datastore/operation/MySQL/commit", 2),
    ("Datastore/operation/MySQL/rollback", 1),
    (f"Datastore/instance/MySQL/{instance_hostname(DB_SETTINGS['host'])}/{DB_SETTINGS['port']}", 12),
]


@validate_transaction_metrics(
    "test_database:test_connect_using_alias",
    scoped_metrics=_test_connect_using_alias_scoped_metrics,
    rollup_metrics=_test_connect_using_alias_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=dict)
@background_task()
def test_connect_using_alias(table_name):
    assert mysql_version is not None
    connection = mysql.connector.connect(
        db=DB_SETTINGS["name"],
        user=DB_SETTINGS["user"],
        passwd=DB_SETTINGS["password"],
        host=DB_SETTINGS["host"],
        port=DB_SETTINGS["port"],
    )

    cursor = connection.cursor()

    cursor.execute(f"""drop table if exists `{table_name}`""")

    cursor.execute(f"""create table {table_name} (a integer, b real, c text)""")

    cursor.executemany(
        f"insert into `{table_name}` values (%(a)s, %(b)s, %(c)s)",
        [{"a": 1, "b": 1.0, "c": "1.0"}, {"a": 2, "b": 2.2, "c": "2.2"}, {"a": 3, "b": 3.3, "c": "3.3"}],
    )

    cursor.execute(f"""select * from {table_name}""")

    for row in cursor:
        pass

    cursor.execute(
        f"update `{table_name}` set a=%(a)s, b=%(b)s, c=%(c)s where a=%(old_a)s",
        {"a": 4, "b": 4.0, "c": "4.0", "old_a": 1},
    )

    cursor.execute(f"""delete from `{table_name}` where a=2""")

    cursor.execute(f"""drop procedure if exists {DB_PROCEDURE}""")
    cursor.execute(
        f"""CREATE PROCEDURE {DB_PROCEDURE}()
                      BEGIN
                        SELECT 'Hello World!';
                      END"""
    )

    cursor.callproc(f"{DB_PROCEDURE}")

    connection.commit()
    connection.rollback()
    connection.commit()
