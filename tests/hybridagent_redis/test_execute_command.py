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

import redis
from opentelemetry.instrumentation.redis import RedisInstrumentor

from testing_support.db_settings import redis_settings
from testing_support.fixtures import override_application_settings, dt_enabled
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

DB_SETTINGS = redis_settings()[0]
REDIS_PY_VERSION = get_package_version_tuple("redis")

@pytest.fixture(scope="module", autouse=True)
def instrument_otel_redis(tracer_provider):
    RedisInstrumentor().instrument(tracer_provider=tracer_provider)


# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Redis/{_host}/{_port}"

_exact_intrinsics = {"type": "Span"}
_exact_root_intrinsics = _exact_intrinsics.copy().update({"nr.entryPoint": True})
_expected_intrinsics = ["traceId", "transactionId", "sampled", "priority", "timestamp", "duration", "name", "category", "guid"]
_expected_root_intrinsics = _expected_intrinsics.copy() + ["transaction.name"]
_expected_child_intrinsics = _expected_intrinsics.copy() + ["parentId"]
_unexpected_root_intrinsics = ["parentId"]
_unexpected_child_intrinsics = ["nr.entryPoint", "transaction.name"]

_exact_agents_instance_enabled = {
    "db.system": "Redis",
    "server.port": DB_SETTINGS["port"],
}
_exact_agents_instance_disabled = {
    "db.system": "Redis",
}
_expected_agents = [
    "db.operation",
    "peer.hostname",
    "server.address",
    "peer.address",
]
_unexpected_agents_instance_disabled = [
    "server.port",
]
_exact_users = {
    "db.system": "redis",
    "db.redis.database_index": 0,
    "net.peer.port": DB_SETTINGS["port"],
    "net.transport": "ip_tcp",
}
_expected_users = [
    "db.statement",
    "net.peer.name",
]

def exercise_redis_multi_args(client):
    client.execute_command("CLIENT", "LIST", parse="LIST")


def exercise_redis_single_arg(client):
    client.execute_command("CLIENT LIST")


@override_application_settings(_enable_instance_settings)
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents_instance_enabled,
    expected_agents=_expected_agents,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_execute_command:test_strict_redis_execute_command_two_args_enable",
    scoped_metrics=[("Datastore/operation/Redis/CLIENT", 1)],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Redis/all", 1),
        ("Datastore/Redis/allOther", 1),
        ("Datastore/operation/Redis/CLIENT", 1),
        (_instance_metric_name, 1),
    ],
    background_task=True,
)
@background_task()
def test_strict_redis_execute_command_two_args_enable():
    r = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_multi_args(r)


@override_application_settings(_disable_instance_settings)
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents_instance_disabled,
    expected_agents=_expected_agents,
    unexpected_agents=_unexpected_agents_instance_disabled,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_execute_command:test_strict_redis_execute_command_two_args_disabled",
    scoped_metrics=[("Datastore/operation/Redis/CLIENT", 1)],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Redis/all", 1),
        ("Datastore/Redis/allOther", 1),
        ("Datastore/operation/Redis/CLIENT", 1),
        (_instance_metric_name, None),
    ],
    background_task=True,
)
@background_task()
def test_strict_redis_execute_command_two_args_disabled():
    r = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_multi_args(r)


@override_application_settings(_enable_instance_settings)
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents_instance_enabled,
    expected_agents=_expected_agents,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_execute_command:test_redis_execute_command_two_args_enable",
    scoped_metrics=[("Datastore/operation/Redis/CLIENT", 1)],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Redis/all", 1),
        ("Datastore/Redis/allOther", 1),
        ("Datastore/operation/Redis/CLIENT", 1),
        (_instance_metric_name, 1),
    ],
    background_task=True,
)
@background_task()
def test_redis_execute_command_two_args_enable():
    r = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_multi_args(r)


@override_application_settings(_disable_instance_settings)
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents_instance_disabled,
    expected_agents=_expected_agents,
    unexpected_agents=_unexpected_agents_instance_disabled,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_execute_command:test_redis_execute_command_two_args_disabled",
    scoped_metrics=[("Datastore/operation/Redis/CLIENT", 1)],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Redis/all", 1),
        ("Datastore/Redis/allOther", 1),
        ("Datastore/operation/Redis/CLIENT", 1),
        (_instance_metric_name, None),
    ],
    background_task=True,
)
@background_task()
def test_redis_execute_command_two_args_disabled():
    r = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_multi_args(r)


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10), reason="This command is not implemented yet")
@override_application_settings(_enable_instance_settings)
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents_instance_enabled,
    expected_agents=_expected_agents,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_execute_command:test_strict_redis_execute_command_as_one_arg_enable",
    scoped_metrics=[("Datastore/operation/Redis/CLIENT LIST", 1)],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Redis/all", 1),
        ("Datastore/Redis/allOther", 1),
        ("Datastore/operation/Redis/CLIENT LIST", 1),
        (_instance_metric_name, 1),
    ],
    background_task=True,
)
@background_task()
def test_strict_redis_execute_command_as_one_arg_enable():
    r = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_single_arg(r)


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10), reason="This command is not implemented yet")
@override_application_settings(_disable_instance_settings)
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents_instance_disabled,
    expected_agents=_expected_agents,
    unexpected_agents=_unexpected_agents_instance_disabled,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_execute_command:test_strict_redis_execute_command_as_one_arg_disabled",
    scoped_metrics=[("Datastore/operation/Redis/CLIENT LIST", 1)],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Redis/all", 1),
        ("Datastore/Redis/allOther", 1),
        ("Datastore/operation/Redis/CLIENT LIST", 1),
        (_instance_metric_name, None),
    ],
    background_task=True,
)
@background_task()
def test_strict_redis_execute_command_as_one_arg_disabled():
    r = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_single_arg(r)


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10), reason="This command is not implemented yet")
@override_application_settings(_enable_instance_settings)
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents_instance_enabled,
    expected_agents=_expected_agents,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_execute_command:test_redis_execute_command_as_one_arg_enable",
    scoped_metrics=[("Datastore/operation/Redis/CLIENT LIST", 1)],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Redis/all", 1),
        ("Datastore/Redis/allOther", 1),
        ("Datastore/operation/Redis/CLIENT LIST", 1),
        (_instance_metric_name, 1),
    ],
    background_task=True,
)
@background_task()
def test_redis_execute_command_as_one_arg_enable():
    r = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_single_arg(r)


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10), reason="This command is not implemented yet")
@override_application_settings(_disable_instance_settings)
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents_instance_disabled,
    expected_agents=_expected_agents,
    unexpected_agents=_unexpected_agents_instance_disabled,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_execute_command:test_redis_execute_command_as_one_arg_disabled",
    scoped_metrics=[("Datastore/operation/Redis/CLIENT LIST", 1)],
    rollup_metrics=[
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Redis/all", 1),
        ("Datastore/Redis/allOther", 1),
        ("Datastore/operation/Redis/CLIENT LIST", 1),
        (_instance_metric_name, None),
    ],
    background_task=True,
)
@background_task()
def test_redis_execute_command_as_one_arg_disabled():
    r = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_single_arg(r)