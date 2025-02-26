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
from testing_support.db_settings import redis_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.time_trace import current_trace
from newrelic.common.package_version_utils import get_package_version_tuple

DB_SETTINGS = redis_settings()[0]
REDIS_PY_VERSION = get_package_version_tuple("redis")

# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = (
    ("Datastore/operation/Redis/scan_iter", 1),
    ("Datastore/operation/Redis/sscan_iter", 1),
    ("Datastore/operation/Redis/zscan_iter", 1),
    ("Datastore/operation/Redis/hscan_iter", 1),
    ("Datastore/operation/Redis/set", 1),
    ("Datastore/operation/Redis/sadd", 1),
    ("Datastore/operation/Redis/zadd", 1),
    ("Datastore/operation/Redis/hset", 1),
)

_base_rollup_metrics = (
    ("Datastore/all", 8),
    ("Datastore/allOther", 8),
    ("Datastore/Redis/all", 8),
    ("Datastore/Redis/allOther", 8),
    ("Datastore/operation/Redis/scan_iter", 1),
    ("Datastore/operation/Redis/sscan_iter", 1),
    ("Datastore/operation/Redis/zscan_iter", 1),
    ("Datastore/operation/Redis/hscan_iter", 1),
    ("Datastore/operation/Redis/set", 1),
    ("Datastore/operation/Redis/sadd", 1),
    ("Datastore/operation/Redis/zadd", 1),
    ("Datastore/operation/Redis/hset", 1),
)

_disable_rollup_metrics = list(_base_rollup_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Redis/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, 8))

_disable_rollup_metrics.append((_instance_metric_name, None))

# Operations


def exercise_redis(client):
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


async def exercise_redis_async(client):
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
    "test_generators:test_strict_redis_generator_enable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_redis_generator_enable_instance():
    client = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis(client)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_strict_redis_generator_disable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_redis_generator_disable_instance():
    client = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis(client)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_redis_generator_enable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_redis_generator_enable_instance():
    client = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis(client)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_redis_generator_disable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_redis_generator_disable_instance():
    client = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis(client)


@pytest.mark.skipif(REDIS_PY_VERSION < (4, 2), reason="Redis.asyncio was not added until v4.2")
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_redis_async_generator_enable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_redis_async_generator_enable_instance(loop):
    client = redis.asyncio.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    loop.run_until_complete(exercise_redis_async(client))


@pytest.mark.skipif(REDIS_PY_VERSION < (4, 2), reason="Redis.asyncio was not added until v4.2")
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_generators:test_redis_async_generator_disable_instance",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_redis_async_generator_disable_instance(loop):
    client = redis.asyncio.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    loop.run_until_complete(exercise_redis_async(client))
