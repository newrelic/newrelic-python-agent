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

import pytest
from testing_support.db_settings import redis_settings
from testing_support.fixture.event_loop import event_loop as loop  # noqa: F401
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

# Settings

DB_SETTINGS = redis_settings()[0]
REDIS_VERSION = get_package_version_tuple("redis")

# Metrics

_enable_scoped_metrics = [("Datastore/operation/Redis/publish", 3)]

_enable_rollup_metrics = [
    ("Datastore/all", 3),
    ("Datastore/allOther", 3),
    ("Datastore/Redis/all", 3),
    ("Datastore/Redis/allOther", 3),
    ("Datastore/operation/Redis/publish", 3),
    ("Datastore/instance/Redis/%s/%s" % (instance_hostname(DB_SETTINGS["host"]), DB_SETTINGS["port"]), 3),
]

# Tests


@pytest.fixture()
def client(loop):  # noqa
    import redis.asyncio

    return loop.run_until_complete(redis.asyncio.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0))


@pytest.mark.skipif(REDIS_VERSION < (4, 2), reason="This functionality exists in Redis 4.2+")
@validate_transaction_metrics("test_asyncio:test_async_pipeline", background_task=True)
@background_task()
def test_async_pipeline(client, loop):  # noqa
    async def _test_pipeline(client):
        async with client.pipeline(transaction=True) as pipe:
            await pipe.set("key1", "value1")
            await pipe.execute()

    loop.run_until_complete(_test_pipeline(client))


@pytest.mark.skipif(REDIS_VERSION < (4, 2), reason="This functionality exists in Redis 4.2+")
@validate_transaction_metrics(
    "test_asyncio:test_async_pubsub",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_async_pubsub(client, loop):  # noqa
    messages_received = []

    async def reader(pubsub):
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                messages_received.append(message["data"].decode())
                if message["data"].decode() == "NOPE":
                    break

    async def _test_pubsub():
        async with client.pubsub() as pubsub:
            await pubsub.psubscribe("channel:*")

            future = asyncio.create_task(reader(pubsub))

            await client.publish("channel:1", "Hello")
            await client.publish("channel:2", "World")
            await client.publish("channel:1", "NOPE")

            await future

    loop.run_until_complete(_test_pubsub())
    assert messages_received == ["Hello", "World", "NOPE"]
