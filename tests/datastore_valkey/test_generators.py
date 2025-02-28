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
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.time_trace import current_trace

DB_SETTINGS = valkey_settings()[0]

# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = (
    ("Datastore/operation/Valkey/scan_iter", 1),
    ("Datastore/operation/Valkey/sscan_iter", 1),
    ("Datastore/operation/Valkey/zscan_iter", 1),
    ("Datastore/operation/Valkey/hscan_iter", 1),
    ("Datastore/operation/Valkey/set", 1),
    ("Datastore/operation/Valkey/sadd", 1),
    ("Datastore/operation/Valkey/zadd", 1),
    ("Datastore/operation/Valkey/hset", 1),
)

_base_rollup_metrics = (
    ("Datastore/all", 8),
    ("Datastore/allOther", 8),
    ("Datastore/Valkey/all", 8),
    ("Datastore/Valkey/allOther", 8),
    ("Datastore/operation/Valkey/scan_iter", 1),
    ("Datastore/operation/Valkey/sscan_iter", 1),
    ("Datastore/operation/Valkey/zscan_iter", 1),
    ("Datastore/operation/Valkey/hscan_iter", 1),
    ("Datastore/operation/Valkey/set", 1),
    ("Datastore/operation/Valkey/sadd", 1),
    ("Datastore/operation/Valkey/zadd", 1),
    ("Datastore/operation/Valkey/hset", 1),
)

_disable_rollup_metrics = list(_base_rollup_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Valkey/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, 8))

_disable_rollup_metrics.append((_instance_metric_name, None))

# Operations


def exercise_valkey(client):
    """
    Exercise client generators by iterating on various methods and ensuring they are
    non-empty, and that traces are started and stopped with the generator.
    """

    # Set existing values
    client.set("scan-key", "value")
    client.sadd("sscan-key", "value")
    client.zadd("zscan-key", {"value": 1})
    client.hset("hscan-key", "field", "value")

    # Check generators
    flag = False
    assert not isinstance(current_trace(), DatastoreTrace)  # Assert no active DatastoreTrace
    for k in client.scan_iter("scan-*"):
        assert k == b"scan-key"
        assert isinstance(current_trace(), DatastoreTrace)  # Assert DatastoreTrace now active
        flag = True
    assert flag

    flag = False
    assert not isinstance(current_trace(), DatastoreTrace)  # Assert no active DatastoreTrace
    for k in client.sscan_iter("sscan-key"):
        assert k == b"value"
        assert isinstance(current_trace(), DatastoreTrace)  # Assert DatastoreTrace now active
        flag = True
    assert flag

    flag = False
    assert not isinstance(current_trace(), DatastoreTrace)  # Assert no active DatastoreTrace
    for k, _ in client.zscan_iter("zscan-key"):
        assert k == b"value"
        assert isinstance(current_trace(), DatastoreTrace)  # Assert DatastoreTrace now active
        flag = True
    assert flag

    flag = False
    assert not isinstance(current_trace(), DatastoreTrace)  # Assert no active DatastoreTrace
    for f, v in client.hscan_iter("hscan-key"):
        assert f == b"field"
        assert v == b"value"
        assert isinstance(current_trace(), DatastoreTrace)  # Assert DatastoreTrace now active
        flag = True
    assert flag


async def exercise_valkey_async(client):
    """
    Exercise client generators by iterating on various methods and ensuring they are
    non-empty, and that traces are started and stopped with the generator.
    """

    # Set existing values
    await client.set("scan-key", "value")
    await client.sadd("sscan-key", "value")
    await client.zadd("zscan-key", {"value": 1})
    await client.hset("hscan-key", "field", "value")

    # Check generators
    flag = False
    assert not isinstance(current_trace(), DatastoreTrace)  # Assert no active DatastoreTrace
    async for k in client.scan_iter("scan-*"):
        assert k == b"scan-key"
        assert isinstance(current_trace(), DatastoreTrace)  # Assert DatastoreTrace now active
        flag = True
    assert flag

    flag = False
    assert not isinstance(current_trace(), DatastoreTrace)  # Assert no active DatastoreTrace
    async for k in client.sscan_iter("sscan-key"):
        assert k == b"value"
        assert isinstance(current_trace(), DatastoreTrace)  # Assert DatastoreTrace now active
        flag = True
    assert flag

    flag = False
    assert not isinstance(current_trace(), DatastoreTrace)  # Assert no active DatastoreTrace
    async for k, _ in client.zscan_iter("zscan-key"):
        assert k == b"value"
        assert isinstance(current_trace(), DatastoreTrace)  # Assert DatastoreTrace now active
        flag = True
    assert flag

    flag = False
    assert not isinstance(current_trace(), DatastoreTrace)  # Assert no active DatastoreTrace
    async for f, v in client.hscan_iter("hscan-key"):
        assert f == b"field"
        assert v == b"value"
        assert isinstance(current_trace(), DatastoreTrace)  # Assert DatastoreTrace now active
        flag = True
    assert flag


# Tests


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_strict_valkey_generator_enable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_valkey_generator_enable_instance():
    client = valkey.StrictValkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey(client)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_strict_valkey_generator_disable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_valkey_generator_disable_instance():
    client = valkey.StrictValkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey(client)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_valkey_generator_enable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_generator_enable_instance():
    client = valkey.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey(client)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_valkey_generator_disable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_generator_disable_instance():
    client = valkey.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_valkey(client)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_valkey_async_generator_enable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_async_generator_enable_instance(loop):
    client = valkey.asyncio.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    loop.run_until_complete(exercise_valkey_async(client))


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_valkey_async_generator_disable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_valkey_async_generator_disable_instance(loop):
    client = valkey.asyncio.Valkey(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    loop.run_until_complete(exercise_valkey_async(client))
