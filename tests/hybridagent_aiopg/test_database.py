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

import asyncio

import aiopg
import pytest
from testing_support.db_settings import postgresql_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

DB_SETTINGS = postgresql_settings()[0]

# Metrics
_base_scoped_metrics = (
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/insert", 1),
    ("Datastore/operation/postgresql/create", 1),
)

_base_rollup_metrics = (
    ("Datastore/all", 2),
    ("Datastore/allOther", 2),
    ("Datastore/postgresql/all", 2),
    ("Datastore/postgresql/allOther", 2),
    (f"Datastore/statement/postgresql/{DB_SETTINGS['table_name']}/insert", 1),
    ("Datastore/operation/postgresql/insert", 1),
    ("Datastore/operation/postgresql/create", 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/postgresql/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, 2))

_disable_rollup_metrics.append((_instance_metric_name, None))


# Query
async def _execute(cursor):
    await cursor.execute(f"CREATE TABLE IF NOT EXISTS {DB_SETTINGS['table_name']} (testField INTEGER)")
    await cursor.execute(f"INSERT INTO {DB_SETTINGS['table_name']} (testField) VALUES (123)")

    cursor.close()


async def _connect_db():
    dsn = f"dbname={DB_SETTINGS['name']} user={DB_SETTINGS['user']} password={DB_SETTINGS['password']} host={DB_SETTINGS['host']} port={DB_SETTINGS['port']}"
    connection = await aiopg.connect(dsn=dsn)

    try:
        cursor = await connection.cursor()
        await _execute(cursor)
    finally:
        connection.close()


async def _create_pool_db():
    dsn = f"dbname={DB_SETTINGS['name']} user={DB_SETTINGS['user']} password={DB_SETTINGS['password']} host={DB_SETTINGS['host']} port={DB_SETTINGS['port']}"
    pool = await aiopg.create_pool(dsn=dsn)

    try:
        connection = await pool.acquire()
        cursor = await connection.cursor()
        await _execute(cursor)
    finally:
        connection.close()


# Tests
@pytest.mark.parametrize(
    "db_instance_reporting,otel_traces_enabled", [(True, True), (True, False), (False, True), (False, False)]
)
def test_connect(db_instance_reporting, otel_traces_enabled):
    kwargs = {}
    if otel_traces_enabled:
        kwargs = {
            "scoped_metrics": _enable_scoped_metrics if db_instance_reporting else _disable_scoped_metrics,
            "rollup_metrics": _enable_rollup_metrics if db_instance_reporting else _disable_rollup_metrics,
        }

    @override_application_settings(
        {
            "datastore_tracer.instance_reporting.enabled": db_instance_reporting,
            "opentelemetry.traces.enabled": otel_traces_enabled,
        }
    )
    @validate_transaction_metrics("test_database:test_connect.<locals>._test", background_task=True, **kwargs)
    @background_task()
    def _test():
        async def _inner_test():
            await _connect_db()

        asyncio.run(_inner_test())

    _test()


@pytest.mark.parametrize("db_instance_reporting", (True, False))
def test_connect_disable_otel_traces(db_instance_reporting):
    with pytest.raises(AssertionError):
        # This will expectedly fail when the metrics are not recorded
        @override_application_settings(
            {
                "datastore_tracer.instance_reporting.enabled": db_instance_reporting,
                "opentelemetry.traces.enabled": False,
            }
        )
        @validate_transaction_metrics(
            "test_database:test_connect.<locals>._test",
            scoped_metrics=_enable_scoped_metrics if db_instance_reporting else _disable_scoped_metrics,
            rollup_metrics=_enable_rollup_metrics if db_instance_reporting else _disable_rollup_metrics,
            background_task=True,
        )
        @background_task()
        def _test():
            async def _inner_test():
                await _connect_db()

            asyncio.run(_inner_test())

        _test()


@pytest.mark.parametrize(
    "db_instance_reporting,otel_traces_enabled", [(True, True), (True, False), (False, True), (False, False)]
)
def test_create_pool(db_instance_reporting, otel_traces_enabled):
    kwargs = {}
    if otel_traces_enabled:
        kwargs = {
            "scoped_metrics": _enable_scoped_metrics if db_instance_reporting else _disable_scoped_metrics,
            "rollup_metrics": _enable_rollup_metrics if db_instance_reporting else _disable_rollup_metrics,
        }

    @override_application_settings(
        {
            "datastore_tracer.instance_reporting.enabled": db_instance_reporting,
            "opentelemetry.traces.enabled": otel_traces_enabled,
        }
    )
    @validate_transaction_metrics("test_database:test_create_pool.<locals>._test", background_task=True, **kwargs)
    @background_task()
    def _test():
        async def _inner_test():
            await _create_pool_db()

        asyncio.run(_inner_test())

    _test()


@pytest.mark.parametrize("db_instance_reporting", (True, False))
def test_create_pool_disable_otel_traces(db_instance_reporting):
    with pytest.raises(AssertionError):
        # This will expectedly fail when the metrics are not recorded
        @override_application_settings(
            {
                "datastore_tracer.instance_reporting.enabled": db_instance_reporting,
                "opentelemetry.traces.enabled": False,
            }
        )
        @validate_transaction_metrics(
            "test_database:test_create_pool.<locals>._test",
            scoped_metrics=_enable_scoped_metrics if db_instance_reporting else _disable_scoped_metrics,
            rollup_metrics=_enable_rollup_metrics if db_instance_reporting else _disable_rollup_metrics,
            background_task=True,
        )
        @background_task()
        def _test():
            async def _inner_test():
                await _create_pool_db()

            asyncio.run(_inner_test())

        _test()
