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

import MySQLdb
from testing_support.db_settings import mysql_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

DB_MULTIPLE_SETTINGS = mysql_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]
DB_NAMESPACE = DB_SETTINGS["namespace"]

# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = (
    ("Function/MySQLdb:Connect", 1),
    (f"Datastore/statement/MySQL/datastore_mysqldb_{DB_NAMESPACE}/select", 1),
    (f"Datastore/statement/MySQL/datastore_mysqldb_{DB_NAMESPACE}/insert", 1),
    (f"Datastore/statement/MySQL/datastore_mysqldb_{DB_NAMESPACE}/update", 1),
    (f"Datastore/statement/MySQL/datastore_mysqldb_{DB_NAMESPACE}/delete", 1),
    ("Datastore/operation/MySQL/drop", 1),
    ("Datastore/operation/MySQL/create", 1),
    ("Datastore/operation/MySQL/show", 1),
    ("Datastore/operation/MySQL/commit", 2),
    ("Datastore/operation/MySQL/rollback", 1),
)

_base_rollup_metrics = (
    ("Datastore/all", 11),
    ("Datastore/allOther", 11),
    ("Datastore/MySQL/all", 11),
    ("Datastore/MySQL/allOther", 11),
    ("Datastore/operation/MySQL/select", 1),
    (f"Datastore/statement/MySQL/datastore_mysqldb_{DB_NAMESPACE}/select", 1),
    ("Datastore/operation/MySQL/insert", 1),
    (f"Datastore/statement/MySQL/datastore_mysqldb_{DB_NAMESPACE}/insert", 1),
    ("Datastore/operation/MySQL/update", 1),
    (f"Datastore/statement/MySQL/datastore_mysqldb_{DB_NAMESPACE}/update", 1),
    ("Datastore/operation/MySQL/delete", 1),
    (f"Datastore/statement/MySQL/datastore_mysqldb_{DB_NAMESPACE}/delete", 1),
    ("Datastore/operation/MySQL/show", 1),
    ("Datastore/operation/MySQL/drop", 1),
    ("Datastore/operation/MySQL/create", 1),
    ("Datastore/operation/MySQL/commit", 2),
    ("Datastore/operation/MySQL/rollback", 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/MySQL/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, 10))

_disable_rollup_metrics.append((_instance_metric_name, None))

# Query


def _exercise_db(connection, table_name):
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(f"""drop table if exists `{table_name}`""")

            cursor.execute(f"""create table `{table_name}` (a integer, b real, c text)""")

            cursor.executemany(
                f"insert into `{table_name}` values (%s, %s, %s)", [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")]
            )

            cursor.execute(f"""select * from {table_name}""")

            for _ in cursor:
                pass

            cursor.execute(f"update `{table_name}` set a=%s, b=%s, c=%s where a=%s", (4, 4.0, "4.0", 1))

            cursor.execute(f"""delete from `{table_name}` where a=2""")

            cursor.execute("""show grants""")

        connection.commit()
        connection.rollback()
        connection.commit()


# Tests


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_cursor:test_execute_via_cursor_enable",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(tuple)
@background_task()
def test_execute_via_cursor_enable(table_name):
    connection = MySQLdb.connect(
        db=DB_SETTINGS["name"],
        user=DB_SETTINGS["user"],
        passwd=DB_SETTINGS["password"],
        host=DB_SETTINGS["host"],
        port=DB_SETTINGS["port"],
    )
    _exercise_db(connection, table_name)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_cursor:test_execute_via_cursor_disable",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(tuple)
@background_task()
def test_execute_via_cursor_disable(table_name):
    connection = MySQLdb.connect(
        db=DB_SETTINGS["name"],
        user=DB_SETTINGS["user"],
        passwd=DB_SETTINGS["password"],
        host=DB_SETTINGS["host"],
        port=DB_SETTINGS["port"],
    )
    _exercise_db(connection, table_name)
