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

DB_SETTINGS = redis_settings()[0]

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}

_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

_base_scoped_metrics = (
        ('Datastore/operation/Redis/client_list', 1),
)

_base_rollup_metrics = (
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/Redis/all', 2),
        ('Datastore/Redis/allOther', 2),
        ('Datastore/operation/Redis/client_list', 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS['host'])
_port = DB_SETTINGS['port']

_instance_metric_name = 'Datastore/instance/Redis/%s/%s' % (_host, _port)

_enable_rollup_metrics.append(
        (_instance_metric_name, 2)
)

_disable_rollup_metrics.append(
        (_instance_metric_name, None)
)

async def exercise_redis_single_arg(client):
    await client.execute_command('CLIENT LIST')

@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
  "test_execute_command:test_redis_execute_command_as_one_arg_enable",
  scoped_metrics=_enable_scoped_metrics,
  rollup_metrics=_enable_rollup_metrics, 
  background_task=True
)
@background_task()
def test_redis_execute_command_as_one_arg_enable(loop):
    client = aioredis.Redis(host=DB_SETTINGS['host'], port=_port, db=0)
    loop.run_until_complete(exercise_redis_single_arg(client))
  
