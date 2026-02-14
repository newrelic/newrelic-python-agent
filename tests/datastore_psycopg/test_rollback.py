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

from conftest import DB_SETTINGS
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = (("Datastore/operation/Postgres/rollback", 1),)

_base_rollup_metrics = (
    ("Datastore/all", 1),
    ("Datastore/allOther", 1),
    ("Datastore/Postgres/all", 1),
    ("Datastore/Postgres/allOther", 1),
    ("Datastore/operation/Postgres/rollback", 1),
)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Postgres/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, 1))

_disable_rollup_metrics.append((_instance_metric_name, None))

# Query


async def _exercise_db(connection):
    try:
        if hasattr(connection, "__aenter__"):
            async with connection:
                raise RuntimeError("error")
        else:
            with connection:
                raise RuntimeError("error")
    except RuntimeError:
        pass


# Tests


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_rollback:test_rollback_on_exception_enable_instance",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception_enable_instance(loop, connection):
    loop.run_until_complete(_exercise_db(connection))


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_rollback:test_rollback_on_exception_disable_instance",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception_disable_instance(loop, connection):
    loop.run_until_complete(_exercise_db(connection))
