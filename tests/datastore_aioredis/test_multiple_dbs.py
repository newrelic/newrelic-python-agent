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

from conftest import aioredis

import pytest
from conftest import AIOREDIS_VERSION, loop  # noqa
from testing_support.db_settings import redis_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

DB_SETTINGS = redis_settings()

_enable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
}
_disable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
}

_base_scoped_metrics = (
    ("Datastore/operation/Redis/get", 1),
    ("Datastore/operation/Redis/set", 1),
    ("Datastore/operation/Redis/client_list", 1),
)

_base_rollup_metrics = (
    ("Datastore/all", 3),
    ("Datastore/allOther", 3),
    ("Datastore/Redis/all", 3),
    ("Datastore/Redis/allOther", 3),
    ("Datastore/operation/Redis/get", 1),
    ("Datastore/operation/Redis/set", 1),
    ("Datastore/operation/Redis/client_list", 1),
)

_concurrent_scoped_metrics = [
    ("Datastore/operation/Redis/get", 2),
    ("Datastore/operation/Redis/set", 2),
]

_concurrent_rollup_metrics = [
    ("Datastore/all", 4),
    ("Datastore/allOther", 4),
    ("Datastore/Redis/all", 4),
    ("Datastore/Redis/allOther", 4),
    ("Datastore/operation/Redis/set", 2),
    ("Datastore/operation/Redis/get", 2),
]

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)


if len(DB_SETTINGS) > 1:
    redis_instance_1 = DB_SETTINGS[0]
    redis_instance_2 = DB_SETTINGS[1]

    _host_1 = instance_hostname(redis_instance_1["host"])
    _port_1 = redis_instance_1["port"]

    _host_2 = instance_hostname(redis_instance_2["host"])
    _port_2 = redis_instance_2["port"]

    instance_metric_name_1 = "Datastore/instance/Redis/%s/%s" % (_host_1, _port_1)
    instance_metric_name_2 = "Datastore/instance/Redis/%s/%s" % (_host_2, _port_2)

    _enable_rollup_metrics.extend(
        [
            (instance_metric_name_1, 2),
            (instance_metric_name_2, 1),
        ]
    )

    _disable_rollup_metrics.extend(
        [
            (instance_metric_name_1, None),
            (instance_metric_name_2, None),
        ]
    )
    _concurrent_rollup_metrics.extend(
        [
            (instance_metric_name_1, 2),
            (instance_metric_name_2, 2),
        ]
    )


@pytest.fixture(params=("Redis", "StrictRedis"))
def client_set(request, loop):  # noqa
    if len(DB_SETTINGS) > 1:
        if AIOREDIS_VERSION >= (2, 0):
            if request.param == "Redis":
                return (
                    aioredis.Redis(host=DB_SETTINGS[0]["host"], port=DB_SETTINGS[0]["port"], db=0),
                    aioredis.Redis(host=DB_SETTINGS[1]["host"], port=DB_SETTINGS[1]["port"], db=0),
                )
            elif request.param == "StrictRedis":
                return (
                    aioredis.StrictRedis(host=DB_SETTINGS[0]["host"], port=DB_SETTINGS[0]["port"], db=0),
                    aioredis.StrictRedis(host=DB_SETTINGS[1]["host"], port=DB_SETTINGS[1]["port"], db=0),
                )
            else:
                raise NotImplementedError()
        else:
            if request.param == "Redis":
                return (
                    loop.run_until_complete(
                        aioredis.create_redis("redis://%s:%d" % (DB_SETTINGS[0]["host"], DB_SETTINGS[0]["port"]), db=0)
                    ),
                    loop.run_until_complete(
                        aioredis.create_redis("redis://%s:%d" % (DB_SETTINGS[1]["host"], DB_SETTINGS[1]["port"]), db=0)
                    ),
                )
            elif request.param == "StrictRedis":
                pytest.skip("StrictRedis not implemented.")
            else:
                raise NotImplementedError()


async def exercise_redis(client_1, client_2):
    await client_1.set("key", "value")
    await client_1.get("key")

    if hasattr(client_2, "execute_command"):
        await client_2.execute_command("CLIENT", "LIST", parse="LIST")
    else:
        await client_2.execute("CLIENT", "LIST")


@pytest.mark.skipif(len(DB_SETTINGS) < 2, reason="Env not configured with multiple databases")
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_datastores_enabled",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_datastores_enabled(client_set, loop):  # noqa
    loop.run_until_complete(exercise_redis(client_set[0], client_set[1]))


@pytest.mark.skipif(len(DB_SETTINGS) < 2, reason="Env not configured with multiple databases")
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_datastores_disabled",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_datastores_disabled(client_set, loop):  # noqa
    loop.run_until_complete(exercise_redis(client_set[0], client_set[1]))


@pytest.mark.skipif(len(DB_SETTINGS) < 2, reason="Env not configured with multiple databases")
@validate_transaction_metrics(
    "test_multiple_dbs:test_concurrent_calls",
    scoped_metrics=_concurrent_scoped_metrics,
    rollup_metrics=_concurrent_rollup_metrics,
    background_task=True,
)
@override_application_settings(_enable_instance_settings)
@background_task()
def test_concurrent_calls(client_set, loop):  # noqa
    # Concurrent calls made with original instrumenation taken from synchonous Redis
    # instrumentation had a bug where datastore info on concurrent calls to multiple instances
    # would result in all instances reporting as the host/port of the final call made.

    import asyncio

    async def exercise_concurrent():
        await asyncio.gather(*(client.set("key-%d" % i, i) for i, client in enumerate(client_set)))
        await asyncio.gather(*(client.get("key-%d" % i) for i, client in enumerate(client_set)))

    loop.run_until_complete(exercise_concurrent())
