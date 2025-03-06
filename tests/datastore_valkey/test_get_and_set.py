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

import valkey
from testing_support.db_settings import valkey_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

DB_SETTINGS = valkey_settings()[0]

# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = (("Datastore/operation/Valkey/get", 1), ("Datastore/operation/Valkey/set", 1))

_base_rollup_metrics = (
    ("Datastore/all", 2),
    ("Datastore/allOther", 2),
    ("Datastore/Valkey/all", 2),
    ("Datastore/Valkey/allOther", 2),
    ("Datastore/operation/Valkey/get", 1),
    ("Datastore/operation/Valkey/set", 1),
)

_disable_rollup_metrics = list(_base_rollup_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Valkey/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, 2))

_disable_rollup_metrics.append((_instance_metric_name, None))

# Operations


def exercise_valkey(client):
    client.set("key", "value")
    client.get("key")


# Tests


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_get_and_set:test_strict_valkey_operation_enable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_valkey_operation_enable_instance():
    client = valkey.StrictValkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey(client)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_get_and_set:test_strict_valkey_operation_disable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_valkey_operation_disable_instance():
    client = valkey.StrictValkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey(client)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_get_and_set:test_valkey_operation_enable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_operation_enable_instance():
    client = valkey.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey(client)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_get_and_set:test_valkey_operation_disable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_operation_disable_instance():
    client = valkey.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey(client)
