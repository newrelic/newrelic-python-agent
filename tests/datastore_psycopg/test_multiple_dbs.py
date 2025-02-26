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

from conftest import DB_MULTIPLE_SETTINGS, DB_SETTINGS, maybe_await
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}


# Metrics

_base_scoped_metrics = [
    ("Datastore/statement/Postgres/pg_settings/select", 1),
    ("Datastore/operation/Postgres/drop", 1),
    ("Datastore/operation/Postgres/create", 1),
    ("Datastore/operation/Postgres/commit", 2),
]

_base_rollup_metrics = [
    ("Datastore/all", 5),
    ("Datastore/allOther", 5),
    ("Datastore/Postgres/all", 5),
    ("Datastore/Postgres/allOther", 5),
    ("Datastore/statement/Postgres/pg_settings/select", 1),
    ("Datastore/operation/Postgres/drop", 1),
    ("Datastore/operation/Postgres/create", 1),
    ("Datastore/operation/Postgres/commit", 2),
]

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_postgresql_1 = DB_MULTIPLE_SETTINGS[0]
_host_1 = instance_hostname(_postgresql_1["host"])
_port_1 = _postgresql_1["port"]

_postgresql_2 = DB_MULTIPLE_SETTINGS[1]
_host_2 = instance_hostname(_postgresql_2["host"])
_port_2 = _postgresql_2["port"]

_instance_metric_name_1 = f"Datastore/instance/Postgres/{_host_1}/{_port_1}"
_instance_metric_name_2 = f"Datastore/instance/Postgres/{_host_2}/{_port_2}"

_enable_rollup_metrics.extend([(_instance_metric_name_1, 2), (_instance_metric_name_2, 3)])
_disable_rollup_metrics.extend([(_instance_metric_name_1, None), (_instance_metric_name_2, None)])


# Query


async def _exercise_db(multiple_connections):
    connection = multiple_connections[0]
    try:
        cursor = connection.cursor()
        await maybe_await(cursor.execute("SELECT setting from pg_settings where name=%s", ("server_version",)))
        await maybe_await(connection.commit())
    finally:
        await maybe_await(connection.close())

    connection = multiple_connections[1]
    try:
        cursor = connection.cursor()
        await maybe_await(cursor.execute(f"drop table if exists {DB_SETTINGS['table_name']}"))
        await maybe_await(cursor.execute(f"create table {DB_SETTINGS['table_name']} (a integer, b real, c text)"))
        await maybe_await(connection.commit())
    finally:
        await maybe_await(connection.close())


# Tests


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_databases_enable_instance",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_multiple_databases_enable_instance(loop, multiple_connections):
    loop.run_until_complete(_exercise_db(multiple_connections))


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_databases_disable_instance",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_scoped_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_multiple_databases_disable_instance(loop, multiple_connections):
    loop.run_until_complete(_exercise_db(multiple_connections))
