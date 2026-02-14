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

import psycopg
import pytest

try:
    from psycopg import sql
except ImportError:
    sql = None

from conftest import DB_SETTINGS, maybe_await
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

# Settings
_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}


# Metrics
_base_scoped_metrics = (
    ("Datastore/operation/Postgres/commit", 2),
    ("Datastore/operation/Postgres/create", 2),
    ("Datastore/operation/Postgres/drop", 1),
    ("Datastore/operation/Postgres/rollback", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['procedure_name']}/call", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['table_name']}/delete", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['table_name']}/insert", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['table_name']}/select", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['table_name']}/update", 1),
)

_base_rollup_metrics = (
    ("Datastore/all", 11),
    ("Datastore/allOther", 11),
    ("Datastore/Postgres/all", 11),
    ("Datastore/Postgres/allOther", 11),
    ("Datastore/operation/Postgres/call", 1),
    ("Datastore/operation/Postgres/commit", 2),
    ("Datastore/operation/Postgres/create", 2),
    ("Datastore/operation/Postgres/delete", 1),
    ("Datastore/operation/Postgres/drop", 1),
    ("Datastore/operation/Postgres/insert", 1),
    ("Datastore/operation/Postgres/rollback", 1),
    ("Datastore/operation/Postgres/select", 1),
    ("Datastore/operation/Postgres/update", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['procedure_name']}/call", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['table_name']}/delete", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['table_name']}/insert", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['table_name']}/select", 1),
    (f"Datastore/statement/Postgres/{DB_SETTINGS['table_name']}/update", 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Postgres/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, 11))

_disable_rollup_metrics.append((_instance_metric_name, None))


# Query
async def _execute(connection, cursor, row_type, wrapper):
    sql = f"drop table if exists {DB_SETTINGS['table_name']}"
    await maybe_await(cursor.execute(wrapper(sql)))

    sql = f"create table {DB_SETTINGS['table_name']} (a integer, b real, c text)"
    await maybe_await(cursor.execute(wrapper(sql)))

    sql = f"insert into {DB_SETTINGS['table_name']} values (%s, %s, %s) returning a, b, c"
    params = [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")]
    await maybe_await(cursor.executemany(wrapper(sql), params, returning=True))

    # Consume inserted records to check that returning param functions
    records = []
    while True:
        records.append(cursor.fetchone())
        if not cursor.nextset():
            break
    assert len(records) == len(params)

    sql = f"select * from {DB_SETTINGS['table_name']}"
    await maybe_await(cursor.execute(wrapper(sql)))

    if hasattr(cursor, "__aiter__"):
        async for row in cursor:
            assert isinstance(row, row_type)
    else:
        # Iterate on sync cursor
        for row in cursor:
            assert isinstance(row, row_type)

    sql = f"update {DB_SETTINGS['table_name']} set a=%s, b=%s, c=%s where a=%s"
    params = (4, 4.0, "4.0", 1)
    await maybe_await(cursor.execute(wrapper(sql), params))

    sql = f"delete from {DB_SETTINGS['table_name']} where a=2"
    await maybe_await(cursor.execute(wrapper(sql)))

    await maybe_await(connection.commit())

    await maybe_await(
        cursor.execute(
            f"create or replace procedure {DB_SETTINGS['procedure_name']}() \nlanguage plpgsql as $$ begin perform now(); end; $$"
        )
    )
    await maybe_await(cursor.execute(f"call {DB_SETTINGS['procedure_name']}()"))

    await maybe_await(connection.rollback())
    await maybe_await(connection.commit())


async def _exercise_db(connection, row_factory=None, use_cur_context=False, row_type=tuple, wrapper=str):
    kwargs = {"row_factory": row_factory} if row_factory else {}

    try:
        cursor = connection.cursor(**kwargs)
        if use_cur_context:
            if hasattr(cursor, "__aenter__"):
                async with cursor:
                    await _execute(connection, cursor, row_type, wrapper)
            else:
                with cursor:
                    await _execute(connection, cursor, row_type, wrapper)
        else:
            await _execute(connection, cursor, row_type, wrapper)
    finally:
        await maybe_await(connection.close())


_test_matrix = [
    "wrapper,use_cur_context",
    [
        (str, False),
        (str, True),
        (sql.SQL, False),
        (sql.SQL, True),
        (lambda q: sql.Composed([sql.SQL(q)]), False),
        (lambda q: sql.Composed([sql.SQL(q)]), True),
    ],
]


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
def test_execute_via_cursor_enable_instance(loop, connection, wrapper, use_cur_context):
    loop.run_until_complete(_exercise_db(connection, use_cur_context=use_cur_context, row_type=tuple, wrapper=wrapper))


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
def test_execute_via_cursor_disable_instance(loop, connection, wrapper, use_cur_context):
    loop.run_until_complete(_exercise_db(connection, use_cur_context=use_cur_context, row_type=tuple, wrapper=wrapper))


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
def test_execute_via_cursor_dict_enable_instance(loop, connection, wrapper, use_cur_context):
    dict_factory = psycopg.rows.dict_row
    loop.run_until_complete(
        _exercise_db(
            connection, row_factory=dict_factory, use_cur_context=use_cur_context, row_type=dict, wrapper=wrapper
        )
    )


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
def test_execute_via_cursor_dict_disable_instance(loop, connection, wrapper, use_cur_context):
    dict_factory = psycopg.rows.dict_row
    loop.run_until_complete(
        _exercise_db(
            connection, row_factory=dict_factory, use_cur_context=use_cur_context, row_type=dict, wrapper=wrapper
        )
    )
