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

''' The purpose of these tests is to confirm that we will record
record instance info for Redis Blaster commands that go through
redis.Connection:send_command(). Commands that don't use send_command,
like the one that use the fanout client, won't have instance info.
'''

import pytest
import redis
import six

from newrelic.api.background_task import background_task

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.db_settings import redis_settings
from testing_support.util import instance_hostname

DB_SETTINGS = redis_settings()[0]
REDIS_PY_VERSION = redis.VERSION


# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

# We don't record instance metrics when using redis blaster,
# so we just check for base metrics.

_base_scoped_metrics = (
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/set', 1),
)

_base_rollup_metrics = (
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/Redis/all', 2),
        ('Datastore/Redis/allOther', 2),
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/set', 1),
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

# Operations

def exercise_redis(routing_client):
    routing_client.set('key', 'value')
    routing_client.get('key')

def exercise_fanout(cluster):
    with cluster.fanout(hosts='all') as client:
        client.execute_command('CLIENT', 'LIST')

# Tests

@pytest.mark.skipif(six.PY3, reason='Redis Blaster is Python 2 only.')
@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10, 2),
        reason='Redis Blaster requires redis>=2.10.2')
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_rb:test_redis_blaster_operation_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_blaster_operation_enable_instance():
    from rb import Cluster

    cluster = Cluster(
            hosts={0: {'port': DB_SETTINGS['port']}},
            host_defaults={'host': DB_SETTINGS['host']}
    )
    exercise_fanout(cluster)

    client = cluster.get_routing_client()
    exercise_redis(client)


@pytest.mark.skipif(six.PY3, reason='Redis Blaster is Python 2 only.')
@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10,2 ),
        reason='Redis Blaster requires redis>=2.10.2')
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_rb:test_redis_blaster_operation_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_blaster_operation_disable_instance():
    from rb import Cluster

    cluster = Cluster(
            hosts={0: {'port': DB_SETTINGS['port']}},
            host_defaults={'host': DB_SETTINGS['host']}
    )
    exercise_fanout(cluster)

    client = cluster.get_routing_client()
    exercise_redis(client)
