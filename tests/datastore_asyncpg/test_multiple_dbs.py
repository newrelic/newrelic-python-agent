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

import asyncpg
import pytest
from testing_support.db_settings import postgresql_settings
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.util import instance_hostname

from newrelic.api.background_task import background_task

DB_MULTIPLE_SETTINGS = postgresql_settings()

ASYNCPG_VERSION = tuple(int(x) for x in getattr(asyncpg, "__version__", "0.0").split(".")[:2])

if ASYNCPG_VERSION < (0, 11):
    CONNECT_METRICS = []

    # Only 1 statement will be recorded since connect is not captured
    STATEMENT_COUNT = 1

    # 2 DBs are queried
    TOTAL_COUNT = STATEMENT_COUNT * 2
else:
    CONNECT_METRICS = [("Datastore/operation/Postgres/connect", 2)]

    # Two statements are executed per DB - connect / select
    STATEMENT_COUNT = 2

    # 2 DBs are queried
    TOTAL_COUNT = STATEMENT_COUNT * 2


# Settings

_enable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
}
_disable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
}


# Metrics

_base_scoped_metrics = CONNECT_METRICS + [
    ("Datastore/statement/Postgres/pg_settings/select", 2),
]

_base_rollup_metrics = [
    ("Datastore/all", TOTAL_COUNT),
    ("Datastore/allOther", TOTAL_COUNT),
    ("Datastore/Postgres/all", TOTAL_COUNT),
    ("Datastore/Postgres/allOther", TOTAL_COUNT),
    ("Datastore/statement/Postgres/pg_settings/select", 2),
]

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

if len(DB_MULTIPLE_SETTINGS) > 1:
    _postgresql_1 = DB_MULTIPLE_SETTINGS[0]
    _host_1 = instance_hostname(_postgresql_1["host"])
    _port_1 = _postgresql_1["port"]

    _postgresql_2 = DB_MULTIPLE_SETTINGS[1]
    _host_2 = instance_hostname(_postgresql_2["host"])
    _port_2 = _postgresql_2["port"]

    _instance_metric_name_1 = "Datastore/instance/Postgres/%s/%s" % (_host_1, _port_1)
    _instance_metric_name_2 = "Datastore/instance/Postgres/%s/%s" % (_host_2, _port_2)

    _enable_rollup_metrics.extend(
        [
            (_instance_metric_name_1, STATEMENT_COUNT),
            (_instance_metric_name_2, STATEMENT_COUNT),
        ]
    )
    _disable_rollup_metrics.extend([(_instance_metric_name_1, None), (_instance_metric_name_2, None)])


# Query


async def _exercise_db():

    postgresql1 = DB_MULTIPLE_SETTINGS[0]
    postgresql2 = DB_MULTIPLE_SETTINGS[1]

    connection = await asyncpg.connect(
        user=postgresql1["user"],
        password=postgresql1["password"],
        database=postgresql1["name"],
        host=postgresql1["host"],
        port=postgresql1["port"],
    )
    try:
        await connection.execute("SELECT setting from pg_settings where name='server_version'")
    finally:
        await connection.close()

    connection = await asyncpg.connect(
        user=postgresql2["user"],
        password=postgresql2["password"],
        database=postgresql2["name"],
        host=postgresql2["host"],
        port=postgresql2["port"],
    )
    try:
        await connection.execute("SELECT setting from pg_settings where name='server_version'")
    finally:
        await connection.close()


# Tests


@pytest.mark.skipif(
    len(DB_MULTIPLE_SETTINGS) < 2,
    reason="Test environment not configured with multiple databases.",
)
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_databases_enable_instance",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_databases_enable_instance(event_loop):
    event_loop.run_until_complete(_exercise_db())


@pytest.mark.skipif(
    len(DB_MULTIPLE_SETTINGS) < 2,
    reason="Test environment not configured with multiple databases.",
)
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_databases_disable_instance",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_scoped_metrics,
    background_task=True,
)
@background_task()
def test_multiple_databases_disable_instance(event_loop):
    event_loop.run_until_complete(_exercise_db())
