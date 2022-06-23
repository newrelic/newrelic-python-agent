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
import aioredis
from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings)
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.db_settings import redis_settings
from testing_support.util import instance_hostname

DB_SETTINGS = redis_settings()

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

_base_scoped_metrics = (
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/set', 1),
        ('Datastore/operation/Redis/client_list', 1),
)

_base_rollup_metrics = (
        ('Datastore/all', 3),
        ('Datastore/allOther', 3),
        ('Datastore/Redis/all', 3),
        ('Datastore/Redis/allOther', 3),
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/set', 1),
        ('Datastore/operation/Redis/client_list', 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)


if len(DB_SETTINGS) > 1:
    redis_instance_1 = DB_SETTINGS[0]
    redis_instance_2 = DB_SETTINGS[1]

    _host_1 = instance_hostname(redis_instance_1['host'])
    _port_1 = redis_instance_1['port']

    _host_2 = instance_hostname(redis_instance_2['host'])
    _port_2 = redis_instance_2['port']

    instance_metric_name_1 = 'Datastore/instance/Redis/%s/%s' % (_host_1, _port_1)
    instance_metric_name_2 = 'Datastore/instance/Redis/%s/%s' % (_host_2, _port_2)

    _enable_rollup_metrics.extend([
            (instance_metric_name_1, 2),
            (instance_metric_name_2, 1),
    ])

    _disable_rollup_metrics.extend([
            (instance_metric_name_1, None),
            (instance_metric_name_2, None),
    ])
    redis_client_2 = aioredis.Redis(host=DB_SETTINGS[1]['host'], port=DB_SETTINGS[1]['port'], db=0)
    strict_redis_client_2 = aioredis.StrictRedis(host=DB_SETTINGS[1]['host'], port=DB_SETTINGS[1]['port'], db=0)


redis_client_1 = aioredis.Redis(host=DB_SETTINGS[0]['host'], port=DB_SETTINGS[0]['port'], db=0)
strict_redis_client_1 = aioredis.StrictRedis(host=DB_SETTINGS[0]['host'], port=DB_SETTINGS[0]['port'], db=0)


async def exercise_redis(client_1, client_2):
    await client_1.set('key', 'value')
    await client_1.get('key')

    await client_2.execute_command('CLIENT', 'LIST', parse='LIST')


@pytest.mark.skipif(len(DB_SETTINGS) < 2, reason="Env not configured with multiple databases")
@pytest.mark.parametrize("client_set", ([
        (redis_client_1, redis_client_2),
        (strict_redis_client_1, strict_redis_client_2)])
)
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics('test_multiple_dbs:test_multiple_datastores_enabled',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_multiple_datastores_enabled(client_set, loop):
    loop.run_until_complete(exercise_redis(client_set[0], client_set[1]))


@pytest.mark.skipif(len(DB_SETTINGS) < 2, reason="Env not configured with multiple databases")
@pytest.mark.parametrize("client_set", ([
        (redis_client_1, redis_client_2),
        (strict_redis_client_1, strict_redis_client_2)])
)
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics('test_multiple_dbs:test_multiple_datastores_disabled',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_multiple_datastores_disabled(client_set, loop):
    loop.run_until_complete(exercise_redis(client_set[0], client_set[1]))
