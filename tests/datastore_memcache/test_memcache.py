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

import memcache

from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings)
from testing_support.db_settings import memcached_settings
from testing_support.util import instance_hostname

from newrelic.api.background_task import background_task
from newrelic.common.object_wrapper import wrap_function_wrapper

DB_SETTINGS = memcached_settings()[0]
MEMCACHED_ADDR = '%s:%s' % (DB_SETTINGS['host'], DB_SETTINGS['port'])

# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

_base_scoped_metrics = [
        ('Datastore/operation/Memcached/set', 1),
        ('Datastore/operation/Memcached/get', 1),
        ('Datastore/operation/Memcached/delete', 1)]

_base_rollup_metrics = [
        ('Datastore/all', 3),
        ('Datastore/allOther', 3),
        ('Datastore/Memcached/all', 3),
        ('Datastore/Memcached/allOther', 3),
        ('Datastore/operation/Memcached/set', 1),
        ('Datastore/operation/Memcached/get', 1),
        ('Datastore/operation/Memcached/delete', 1)]

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(DB_SETTINGS['host'])
_port = DB_SETTINGS['port']

_instance_metric_name = 'Datastore/instance/Memcached/%s/%s' % (_host, _port)

_enable_rollup_metrics.append(
        (_instance_metric_name, 3)
)

_disable_rollup_metrics.append(
        (_instance_metric_name, None)
)

# Query

def _exercise_db(client):
    key = DB_SETTINGS['namespace'] + 'key'
    client.set(key, 'value')
    value = client.get(key)
    client.delete(key)
    assert value == 'value'

# Tests

@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_memcache:test_set_get_delete_enable',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_set_get_delete_enable():
    client = memcache.Client([MEMCACHED_ADDR])
    _exercise_db(client)

@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_memcache:test_set_get_delete_disable',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_set_get_delete_disable():
    instance_info_called = [False]

    def check_instance_info_call(wrapped, instance, args, kwargs):
        instance_info_called[0] = True

        return wrapped(*args, **kwargs)

    wrap_function_wrapper('newrelic.hooks.datastore_memcache',
            '_instance_info', check_instance_info_call)
    client = memcache.Client([MEMCACHED_ADDR])
    _exercise_db(client)
    assert not instance_info_called[0], "memcached _instance_info was called"
