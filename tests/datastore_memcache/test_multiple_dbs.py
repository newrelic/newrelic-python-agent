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
import memcache

from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings)
from testing_support.db_settings import memcached_settings
from testing_support.util import instance_hostname

DB_MULTIPLE_SETTINGS = memcached_settings()

# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

_base_scoped_metrics = (
    ('Datastore/operation/Memcached/get_multi', 1),
    ('Datastore/operation/Memcached/set_multi', 1),
)

_base_rollup_metrics = (
    ('Datastore/all', 2),
    ('Datastore/allOther', 2),
    ('Datastore/Memcached/all', 2),
    ('Datastore/Memcached/allOther', 2),
    ('Datastore/operation/Memcached/set_multi', 1),
    ('Datastore/operation/Memcached/get_multi', 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

if len(DB_MULTIPLE_SETTINGS) > 1:
    memcached_1 = DB_MULTIPLE_SETTINGS[0]
    memcached_2 = DB_MULTIPLE_SETTINGS[1]

    host_1 = instance_hostname(memcached_1['host'])
    port_1 = memcached_1['port']

    host_2 = instance_hostname(memcached_2['host'])
    port_2 = memcached_2['port']

    instance_metric_name_1 = 'Datastore/instance/Memcached/%s/%s' % (host_1,
            port_1)
    instance_metric_name_2 = 'Datastore/instance/Memcached/%s/%s' % (host_2,
            port_2)

    _enable_rollup_metrics.extend([
            (instance_metric_name_1, None),
            (instance_metric_name_2, None),
    ])

    _disable_rollup_metrics.extend([
            (instance_metric_name_1, None),
            (instance_metric_name_2, None),
    ])

def exercise_memcached(client, multi_dict):
    client.set_multi(multi_dict)
    client.get_multi(multi_dict.keys())

transaction_metric_prefix = 'test_multiple_dbs:test_multiple_datastores'

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(transaction_metric_prefix+'_enabled',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_multiple_datastores_enabled(memcached_multi):
    memcached1 = DB_MULTIPLE_SETTINGS[0]
    memcached2 = DB_MULTIPLE_SETTINGS[1]
    settings = [memcached1, memcached2]
    servers = ["%s:%s" % (x['host'], x['port']) for x in settings]

    client = memcache.Client(servers=servers)

    exercise_memcached(client, memcached_multi)

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(transaction_metric_prefix+'_disabled',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_multiple_datastores_disabled(memcached_multi):
    memcached1 = DB_MULTIPLE_SETTINGS[0]
    memcached2 = DB_MULTIPLE_SETTINGS[1]
    settings = [memcached1, memcached2]
    servers = ["%s:%s" % (x['host'], x['port']) for x in settings]

    client = memcache.Client(servers=servers)

    exercise_memcached(client, memcached_multi)
