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
from uuid import uuid4

import pytest
from testing_support.db_settings import redis_settings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import dt_enabled
from testing_support.util import instance_hostname
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

# Settings

DB_SETTINGS = redis_settings()[0]
REDIS_PY_VERSION = get_package_version_tuple("redis")

# Metrics for publish test

_base_scoped_metrics = [("Datastore/operation/redis/publish", 3)]

_base_rollup_metrics = [
    ("Datastore/all", 3),
    ("Datastore/allOther", 3),
    ("Datastore/redis/all", 3),
    ("Datastore/redis/allOther", 3),
    ("Datastore/operation/redis/publish", 3),
    (f"Datastore/instance/redis/{instance_hostname(DB_SETTINGS['host'])}/{DB_SETTINGS['port']}", 3),
]

# Metrics for connection pool test

_base_pool_scoped_metrics = [
    ("Datastore/operation/redis/get", 1),
    ("Datastore/operation/redis/set", 1),
    ("Datastore/operation/redis/client", 1),
]

_base_pool_rollup_metrics = [
    ("Datastore/all", 3),
    ("Datastore/allOther", 3),
    ("Datastore/redis/all", 3),
    ("Datastore/redis/allOther", 3),
    ("Datastore/operation/redis/get", 1),
    ("Datastore/operation/redis/set", 1),
    ("Datastore/operation/redis/client", 1),
    (f"Datastore/instance/redis/{instance_hostname(DB_SETTINGS['host'])}/{DB_SETTINGS['port']}", 3),
]

# Expected intrinsic, agent, and user metrics

_exact_intrinsics = {"type": "Span"}
_exact_root_intrinsics = _exact_intrinsics.copy().update({"nr.entryPoint": True})
_expected_intrinsics = [
    "traceId",
    "transactionId",
    "sampled",
    "priority",
    "timestamp",
    "duration",
    "name",
    "category",
    "guid",
]
_expected_root_intrinsics = [*_expected_intrinsics, "transaction.name"]
_expected_child_intrinsics = [*_expected_intrinsics, "parentId"]
_unexpected_root_intrinsics = ["parentId"]
_unexpected_child_intrinsics = ["nr.entryPoint", "transaction.name"]

_exact_agents = {"db.system": "redis", "server.port": DB_SETTINGS["port"]}
_expected_agents = ["db.operation", "peer.hostname", "server.address", "peer.address"]
_exact_users = {
    "db.system": "redis",
    "db.redis.database_index": 0,
    "net.peer.port": DB_SETTINGS["port"],
    "net.transport": "ip_tcp",
}
_expected_users = ["db.statement", "net.peer.name"]

# Tests


@pytest.fixture
def client(loop):
    import redis.asyncio

    return loop.run_until_complete(redis.asyncio.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0))


@pytest.fixture
def client_pool(loop):
    import redis.asyncio

    connection_pool = redis.asyncio.ConnectionPool(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    return loop.run_until_complete(redis.asyncio.Redis(connection_pool=connection_pool))


@pytest.mark.skipif(REDIS_PY_VERSION < (4, 2), reason="This functionality exists in Redis 4.2+")
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    count=3,  # GET, SET, CLIENT
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents,
    expected_agents=_expected_agents,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_asyncio:test_async_connection_pool",
    scoped_metrics=_base_pool_scoped_metrics,
    rollup_metrics=_base_pool_rollup_metrics,
    background_task=True,
)
@background_task()
def test_async_connection_pool(client_pool, loop):
    async def _test_async_pool(client_pool):
        await client_pool.set("key1", "value1")
        await client_pool.get("key1")
        await client_pool.execute_command("CLIENT", "LIST")

    loop.run_until_complete(_test_async_pool(client_pool))


@pytest.mark.skipif(REDIS_PY_VERSION < (4, 2), reason="This functionality exists in Redis 4.2+")
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
    exact_agents=_exact_agents,
    expected_agents=_expected_agents,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics("test_asyncio:test_async_pipeline", background_task=True)
@background_task()
def test_async_pipeline(client, loop):
    async def _test_pipeline(client):
        async with client.pipeline(transaction=True) as pipe:
            await pipe.set("key1", "value1")
            await pipe.execute()

    loop.run_until_complete(_test_pipeline(client))


@pytest.mark.skipif(REDIS_PY_VERSION < (4, 2), reason="This functionality exists in Redis 4.2+")
@dt_enabled
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    count=3,  # publish x 3
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
    exact_agents=_exact_agents,
    expected_agents=_expected_agents,
    exact_users=_exact_users,
    expected_users=_expected_users,
)
@validate_transaction_metrics(
    "test_asyncio:test_async_pubsub",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_base_rollup_metrics,
    background_task=True,
)
@background_task()
def test_async_pubsub(client, loop):
    messages_received = []
    message_received = asyncio.Event()

    channel_1 = f"channel:{uuid4()}"
    channel_2 = f"channel:{uuid4()}"

    async def reader(pubsub):
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                message_received.set()
                messages_received.append(message["data"].decode())
                if message["data"].decode() == "NOPE":
                    break

    async def _publish(client, channel, message):
        """Publish a message and wait for the reader to receive it."""
        await client.publish(channel, message)
        await asyncio.wait_for(message_received.wait(), timeout=10)
        message_received.clear()

    async def _test_pubsub():
        async with client.pubsub() as pubsub:
            await pubsub.psubscribe(channel_1, channel_2)

            future = asyncio.create_task(reader(pubsub))

            await _publish(client, channel_1, "Hello")
            await _publish(client, channel_2, "World")
            await _publish(client, channel_1, "NOPE")

            await future

    loop.run_until_complete(_test_pubsub())
    assert messages_received == ["Hello", "World", "NOPE"]
