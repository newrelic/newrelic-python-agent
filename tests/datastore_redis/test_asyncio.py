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

from conftest import async_client as client
from conftest import async_client_pool as client_pool
from testing_support.db_settings import redis_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

# Settings

DB_SETTINGS = redis_settings()[0]

# Metrics for publish test

_base_scoped_metrics = [("Datastore/operation/Redis/publish", 3), ("Datastore/operation/Redis/client_setinfo", 2)]

_base_rollup_metrics = [
    ("Datastore/all", 5),
    ("Datastore/allOther", 5),
    ("Datastore/Redis/all", 5),
    ("Datastore/Redis/allOther", 5),
    ("Datastore/operation/Redis/publish", 3),
    (f"Datastore/instance/Redis/{instance_hostname(DB_SETTINGS['host'])}/{DB_SETTINGS['port']}", 5),
    ("Datastore/operation/Redis/client_setinfo", 2),
]


# Metrics for connection pool test

_base_pool_scoped_metrics = [
    ("Datastore/operation/Redis/get", 1),
    ("Datastore/operation/Redis/set", 1),
    ("Datastore/operation/Redis/client_list", 1),
]

_base_pool_rollup_metrics = [
    ("Datastore/all", 3),
    ("Datastore/allOther", 3),
    ("Datastore/Redis/all", 3),
    ("Datastore/Redis/allOther", 3),
    ("Datastore/operation/Redis/get", 1),
    ("Datastore/operation/Redis/set", 1),
    ("Datastore/operation/Redis/client_list", 1),
    (f"Datastore/instance/Redis/{instance_hostname(DB_SETTINGS['host'])}/{DB_SETTINGS['port']}", 3),
]


# Tests


@validate_transaction_metrics(
    "test_asyncio:test_async_connection_pool",
    scoped_metrics=_base_pool_scoped_metrics,
    rollup_metrics=_base_pool_rollup_metrics,
    background_task=True,
)
@background_task()
def test_async_connection_pool(client_pool, loop):
    client_pool = client_pool()

    async def _test_async_pool(client_pool):
        await client_pool.set("key1", "value1")
        await client_pool.get("key1")
        await client_pool.execute_command("CLIENT", "LIST")

    loop.run_until_complete(_test_async_pool(client_pool))


@validate_transaction_metrics("test_asyncio:test_async_pipeline", background_task=True)
@background_task()
def test_async_pipeline(client, loop):
    client = client()

    async def _test_pipeline(client):
        async with client.pipeline(transaction=True) as pipe:
            await pipe.set("key1", "value1")
            await pipe.execute()

    loop.run_until_complete(_test_pipeline(client))


@validate_transaction_metrics(
    "test_asyncio:test_async_pubsub",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_base_rollup_metrics,
    background_task=True,
)
@background_task()
def test_async_pubsub(client, loop):
    client = client()

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
