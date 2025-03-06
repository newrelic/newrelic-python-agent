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

import pytest
import valkey
from testing_support.db_settings import valkey_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

DB_MULTIPLE_SETTINGS = valkey_settings()


# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = [
    ("Datastore/operation/Valkey/get", 1),
    ("Datastore/operation/Valkey/set", 1),
    ("Datastore/operation/Valkey/client_list", 1),
]

_base_scoped_metrics.append(("Datastore/operation/Valkey/client_setinfo", 2))

datastore_all_metric_count = 5

_base_rollup_metrics = [
    ("Datastore/all", datastore_all_metric_count),
    ("Datastore/allOther", datastore_all_metric_count),
    ("Datastore/Valkey/all", datastore_all_metric_count),
    ("Datastore/Valkey/allOther", datastore_all_metric_count),
    ("Datastore/operation/Valkey/get", 1),
    ("Datastore/operation/Valkey/set", 1),
    ("Datastore/operation/Valkey/client_list", 1),
]

_base_rollup_metrics.append(("Datastore/operation/Valkey/client_setinfo", 2))


if len(DB_MULTIPLE_SETTINGS) > 1:
    valkey_1 = DB_MULTIPLE_SETTINGS[0]
    valkey_2 = DB_MULTIPLE_SETTINGS[1]

    host_1 = instance_hostname(valkey_1["host"])
    port_1 = valkey_1["port"]

    host_2 = instance_hostname(valkey_2["host"])
    port_2 = valkey_2["port"]

    instance_metric_name_1 = f"Datastore/instance/Valkey/{host_1}/{port_1}"
    instance_metric_name_2 = f"Datastore/instance/Valkey/{host_2}/{port_2}"

    instance_metric_name_1_count = 2
    instance_metric_name_2_count = 3

    _enable_rollup_metrics = _base_rollup_metrics.extend(
        [(instance_metric_name_1, instance_metric_name_1_count), (instance_metric_name_2, instance_metric_name_2_count)]
    )

    _disable_rollup_metrics = _base_rollup_metrics.extend(
        [(instance_metric_name_1, None), (instance_metric_name_2, None)]
    )


def exercise_valkey(client_1, client_2):
    client_1.set("key", "value")
    client_1.get("key")

    client_2.execute_command("CLIENT", "LIST", parse="LIST")


@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2, reason="Test environment not configured with multiple databases.")
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_datastores_enabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_datastores_enabled():
    valkey1 = DB_MULTIPLE_SETTINGS[0]
    valkey2 = DB_MULTIPLE_SETTINGS[1]

    client_1 = valkey.StrictValkey(host=valkey1["host"], port=valkey1["port"], db=0)
    client_2 = valkey.StrictValkey(host=valkey2["host"], port=valkey2["port"], db=1)
    exercise_valkey(client_1, client_2)


@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2, reason="Test environment not configured with multiple databases.")
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_datastores_disabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_datastores_disabled():
    valkey1 = DB_MULTIPLE_SETTINGS[0]
    valkey2 = DB_MULTIPLE_SETTINGS[1]

    client_1 = valkey.StrictValkey(host=valkey1["host"], port=valkey1["port"], db=0)
    client_2 = valkey.StrictValkey(host=valkey2["host"], port=valkey2["port"], db=1)
    exercise_valkey(client_1, client_2)
