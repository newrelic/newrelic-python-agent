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
import aredis

from newrelic.api.background_task import background_task

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.db_settings import redis_settings
from testing_support.util import instance_hostname

DB_SETTINGS = redis_settings()[0]
REDIS_PY_VERSION = aredis.VERSION

# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

_base_scoped_metrics = (
        ('Datastore/operation/Redis/client_list', 1),
)

_base_rollup_metrics = (
        ('Datastore/all', 1),
        ('Datastore/allOther', 1),
        ('Datastore/Redis/all', 1),
        ('Datastore/Redis/allOther', 1),
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
        (_instance_metric_name, 1)
)

_disable_rollup_metrics.append(
        (_instance_metric_name, None)
)

async def exercise_redis_multi_args(client):
    await client.execute_command('CLIENT', 'LIST', parse='LIST')

async def exercise_redis_single_arg(client):
    await client.execute_command('CLIENT LIST')


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_two_args_enable',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_two_args_enable(loop):
    r = aredis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    loop.run_until_complete(exercise_redis_multi_args(r))

@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_two_args_disabled',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_two_args_disabled(loop):
    r = aredis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    loop.run_until_complete(exercise_redis_multi_args(r))


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_as_one_arg_enable',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_as_one_arg_enable(loop):
    r = aredis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    loop.run_until_complete(exercise_redis_single_arg(r))

@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_as_one_arg_disabled',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_as_one_arg_disabled(loop):
    r = aredis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    loop.run_until_complete(exercise_redis_single_arg(r))
