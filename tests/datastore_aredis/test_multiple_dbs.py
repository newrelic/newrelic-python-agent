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

import aredis
import pytest
from testing_support.db_settings import redis_settings
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.util import instance_hostname

from newrelic.api.background_task import background_task

DB_MULTIPLE_SETTINGS = redis_settings()

# Settings

_enable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
}
_disable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
}

# Metrics

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
    ("Datastore/operation/Redis/get", 1),
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

if len(DB_MULTIPLE_SETTINGS) > 1:
    redis_1 = DB_MULTIPLE_SETTINGS[0]
    redis_2 = DB_MULTIPLE_SETTINGS[1]

    host_1 = instance_hostname(redis_1["host"])
    port_1 = redis_1["port"]

    host_2 = instance_hostname(redis_2["host"])
    port_2 = redis_2["port"]

    instance_metric_name_1 = "Datastore/instance/Redis/%s/%s" % (host_1, port_1)
    instance_metric_name_2 = "Datastore/instance/Redis/%s/%s" % (host_2, port_2)

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


async def exercise_redis(client_1, client_2):
    await client_1.set("key", "value")
    await client_1.get("key")

    await client_2.execute_command("CLIENT", "LIST", parse="LIST")


@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2, reason="Test environment not configured with multiple databases.")
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_datastores_enabled",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_datastores_enabled(loop):
    redis1 = DB_MULTIPLE_SETTINGS[0]
    redis2 = DB_MULTIPLE_SETTINGS[1]

    client_1 = aredis.StrictRedis(host=redis1["host"], port=redis1["port"], db=0)
    client_2 = aredis.StrictRedis(host=redis2["host"], port=redis2["port"], db=1)
    loop.run_until_complete(exercise_redis(client_1, client_2))


@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2, reason="Test environment not configured with multiple databases.")
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_datastores_disabled",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_datastores_disabled(loop):
    redis1 = DB_MULTIPLE_SETTINGS[0]
    redis2 = DB_MULTIPLE_SETTINGS[1]

    client_1 = aredis.StrictRedis(host=redis1["host"], port=redis1["port"], db=0)
    client_2 = aredis.StrictRedis(host=redis2["host"], port=redis2["port"], db=1)
    loop.run_until_complete(exercise_redis(client_1, client_2))


@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2, reason="Test environment not configured with multiple databases.")
@validate_transaction_metrics(
    "test_multiple_dbs:test_concurrent_calls",
    scoped_metrics=_concurrent_scoped_metrics,
    rollup_metrics=_concurrent_rollup_metrics,
    background_task=True,
)
@override_application_settings(_enable_instance_settings)
@background_task()
def test_concurrent_calls(loop):
    # Concurrent calls made with original instrumenation taken from synchonous Redis
    # instrumentation had a bug where datastore info on concurrent calls to multiple instances
    # would result in all instances reporting as the host/port of the final call made.

    import asyncio

    redis1 = DB_MULTIPLE_SETTINGS[0]
    redis2 = DB_MULTIPLE_SETTINGS[1]

    client_1 = aredis.StrictRedis(host=redis1["host"], port=redis1["port"], db=0)
    client_2 = aredis.StrictRedis(host=redis2["host"], port=redis2["port"], db=1)
    clients = (client_1, client_2)

    async def exercise_concurrent():
        await asyncio.gather(*(client.set("key-%d" % i, i) for i, client in enumerate(clients)))
        await asyncio.gather(*(client.get("key-%d" % i) for i, client in enumerate(clients)))

    loop.run_until_complete(exercise_concurrent())
