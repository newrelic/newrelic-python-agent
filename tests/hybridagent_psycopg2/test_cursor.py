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

import psycopg2
import psycopg2.extensions
import psycopg2.extras
import pytest
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

try:
    from psycopg2 import sql
except ImportError:
    sql = None

from testing_support.db_settings import postgresql_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

Psycopg2Instrumentor().instrument()

DB_SETTINGS = postgresql_settings()[0]


# Settings
_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# NOTE: Regarding differences in supportability metrics seen
# between OpenTelemetry and New Relic agent instrumentation:
# 1. OpenTelemetry does not provide explicit span creation
# for `commit()`/`rollback()` operations.  As a result, these
# operations do not appear in the supportability metrics.
# 2. OpenTelemetry combines `callproc()` operations into
# a single "operation" metric, whereas New Relic agent
# instrumentation creates separate "call" statement metrics
# for each stored procedure called.

# Metrics
_base_scoped_metrics = (
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/select", 1),
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/insert", 1),
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/update", 1),
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/delete", 1),
    ("Datastore/operation/postgresql/now", 1),
    ("Datastore/operation/postgresql/pg_sleep", 1),
    ("Datastore/operation/postgresql/drop", 1),
    ("Datastore/operation/postgresql/create", 1),
)

_base_rollup_metrics = (
    ("Datastore/all", 8),
    ("Datastore/allOther", 8),
    ("Datastore/postgresql/all", 8),
    ("Datastore/postgresql/allOther", 8),
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/select", 1),
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/insert", 1),
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/update", 1),
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/delete", 1),
    ("Datastore/operation/postgresql/select", 1),
    ("Datastore/operation/postgresql/insert", 1),
    ("Datastore/operation/postgresql/update", 1),
    ("Datastore/operation/postgresql/delete", 1),
    ("Datastore/operation/postgresql/drop", 1),
    ("Datastore/operation/postgresql/create", 1),
    ("Datastore/operation/postgresql/now", 1),
    ("Datastore/operation/postgresql/pg_sleep", 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/postgresql/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, 8))

_disable_rollup_metrics.append((_instance_metric_name, None))


# Query
def _execute(connection, cursor, row_type, wrapper):
    unicode_type = psycopg2.extensions.UNICODE
    psycopg2.extensions.register_type(unicode_type)
    psycopg2.extensions.register_type(unicode_type, connection)
    psycopg2.extensions.register_type(unicode_type, cursor)

    sql = f"""drop table if exists {DB_SETTINGS["table_name"]}"""
    cursor.execute(wrapper(sql))

    sql = f"""create table {DB_SETTINGS["table_name"]} (a integer, b real, c text)"""
    cursor.execute(wrapper(sql))

    sql = f"insert into {DB_SETTINGS['table_name']} values (%s, %s, %s)"
    params = [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")]
    cursor.executemany(wrapper(sql), params)

    sql = f"""select * from {DB_SETTINGS["table_name"]}"""
    cursor.execute(wrapper(sql))

    for row in cursor:
        assert isinstance(row, row_type)

    sql = f"update {DB_SETTINGS['table_name']} set a=%s, b=%s, c=%s where a=%s"
    params = (4, 4.0, "4.0", 1)
    cursor.execute(wrapper(sql), params)

    sql = f"""delete from {DB_SETTINGS["table_name"]} where a=2"""
    cursor.execute(wrapper(sql))

    connection.commit()

    cursor.callproc("now")
    cursor.callproc("pg_sleep", (0.0,))

    connection.rollback()
    connection.commit()


def _exercise_db(cursor_factory=None, use_cur_context=False, row_type=tuple, wrapper=str):
    # Note that this is slightly different from the NR test setup.
    # OTel only supports cursor_factories when they are passed in
    # as a connection parameter.  If passed in via cursor() method,
    # they are not instrumented.  For more information:
    # https://github.com/open-telemetry/opentelemetry-python-contrib/issues/578
    kwargs = {
        "database": DB_SETTINGS["name"],
        "user": DB_SETTINGS["user"],
        "password": DB_SETTINGS["password"],
        "host": DB_SETTINGS["host"],
        "port": DB_SETTINGS["port"],
    }
    if cursor_factory:
        kwargs["cursor_factory"] = cursor_factory

    connection = psycopg2.connect(**kwargs)

    try:
        if use_cur_context:
            with connection.cursor() as cursor:
                _execute(connection, cursor, row_type, wrapper)
        else:
            cursor = connection.cursor()
            _execute(connection, cursor, row_type, wrapper)
    finally:
        connection.close()


_test_matrix = ["wrapper,use_cur_context", [(str, False)]]


# with statement support for connections/cursors added in 2.5 and up
_test_matrix[1].append((str, True))

# Composable SQL is expected to be available in versions 2.7 and up
assert sql, "Composable sql (from psycopg2 import sql) is expected to load but is not loading"

# exercise with regular SQL wrapper
_test_matrix[1].append((sql.SQL, True))
_test_matrix[1].append((sql.SQL, False))

# exercise with "Composed" SQL object
_test_matrix[1].append((lambda q: sql.Composed([sql.SQL(q)]), True))
_test_matrix[1].append((lambda q: sql.Composed([sql.SQL(q)]), False))


# Tests
@pytest.mark.parametrize(*_test_matrix)
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_cursor:test_execute_via_cursor_enable_instance",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_enable_instance(wrapper, use_cur_context):
    _exercise_db(cursor_factory=None, use_cur_context=use_cur_context, row_type=tuple, wrapper=wrapper)


@pytest.mark.parametrize(*_test_matrix)
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_cursor:test_execute_via_cursor_disable_instance",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_disable_instance(wrapper, use_cur_context):
    _exercise_db(cursor_factory=None, use_cur_context=use_cur_context, row_type=tuple, wrapper=wrapper)


@pytest.mark.parametrize(*_test_matrix)
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_cursor:test_execute_via_cursor_dict_enable_instance",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict_enable_instance(wrapper, use_cur_context):
    dict_factory = psycopg2.extras.RealDictCursor
    _exercise_db(cursor_factory=dict_factory, use_cur_context=use_cur_context, row_type=dict, wrapper=wrapper)


@pytest.mark.parametrize(*_test_matrix)
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_cursor:test_execute_via_cursor_dict_disable_instance",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict_disable_instance(wrapper, use_cur_context):
    dict_factory = psycopg2.extras.RealDictCursor
    _exercise_db(cursor_factory=dict_factory, use_cur_context=use_cur_context, row_type=dict, wrapper=wrapper)
