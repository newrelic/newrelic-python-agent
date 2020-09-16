import asyncio
import asyncpg
import pytest

from testing_support.fixtures import (
    validate_transaction_metrics,
    validate_database_trace_inputs,
    override_application_settings,
)
from testing_support.util import instance_hostname
from utils import DB_MULTIPLE_SETTINGS

from newrelic.api.background_task import background_task


# Settings

_enable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
}
_disable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
}


# Metrics

_base_scoped_metrics = [
    ("Datastore/statement/Postgres/pg_settings/select", 2),
]

_base_rollup_metrics = [
    ("Datastore/all", 4),
    ("Datastore/allOther", 4),
    ("Datastore/Postgres/all", 4),
    ("Datastore/Postgres/allOther", 4),
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
        [(_instance_metric_name_1, 1), (_instance_metric_name_2, 1)]
    )
    _disable_rollup_metrics.extend(
        [(_instance_metric_name_1, None), (_instance_metric_name_2, None)]
    )


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
def test_multiple_databases_enable_instance():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_exercise_db())


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
def test_multiple_databases_disable_instance():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_exercise_db())
