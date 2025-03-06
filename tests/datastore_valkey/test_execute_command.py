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

_base_scoped_metrics = [("Datastore/operation/Valkey/client_list", 1)]

_base_scoped_metrics.append(("Datastore/operation/Valkey/client_setinfo", 2))

_base_rollup_metrics = [
    ("Datastore/all", 3),
    ("Datastore/allOther", 3),
    ("Datastore/Valkey/all", 3),
    ("Datastore/Valkey/allOther", 3),
    ("Datastore/operation/Valkey/client_list", 1),
]
_base_rollup_metrics.append(("Datastore/operation/Valkey/client_setinfo", 2))

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Valkey/{_host}/{_port}"

instance_metric_count = 3

_enable_rollup_metrics = _base_rollup_metrics.append((_instance_metric_name, instance_metric_count))

_disable_rollup_metrics = _base_rollup_metrics.append((_instance_metric_name, None))


def exercise_valkey_multi_args(client):
    client.execute_command("CLIENT", "LIST", parse="LIST")


def exercise_valkey_single_arg(client):
    client.execute_command("CLIENT LIST")


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_strict_valkey_execute_command_two_args_enable",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_valkey_execute_command_two_args_enable():
    r = valkey.StrictValkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey_multi_args(r)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_strict_valkey_execute_command_two_args_disabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_valkey_execute_command_two_args_disabled():
    r = valkey.StrictValkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey_multi_args(r)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_valkey_execute_command_two_args_enable",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_execute_command_two_args_enable():
    r = valkey.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey_multi_args(r)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_valkey_execute_command_two_args_disabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_execute_command_two_args_disabled():
    r = valkey.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey_multi_args(r)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_strict_valkey_execute_command_as_one_arg_enable",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_valkey_execute_command_as_one_arg_enable():
    r = valkey.StrictValkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey_single_arg(r)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_strict_valkey_execute_command_as_one_arg_disabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_valkey_execute_command_as_one_arg_disabled():
    r = valkey.StrictValkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey_single_arg(r)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_valkey_execute_command_as_one_arg_enable",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_execute_command_as_one_arg_enable():
    r = valkey.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey_single_arg(r)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_valkey_execute_command_as_one_arg_disabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_execute_command_as_one_arg_disabled():
    r = valkey.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey_single_arg(r)
