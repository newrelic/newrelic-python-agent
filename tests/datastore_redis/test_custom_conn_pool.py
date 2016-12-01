''' The purpose of these tests is to confirm that using non-standard
connection pool does not result in an error. For instance, Redis Blaster
uses a custom connection pool, which does not have a `connection_kwargs`
attribute. As a result, we do not record datastore instance info when
redis blaster is being used.
'''

import pytest
import redis
import six

from newrelic.agent import background_task

from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings)
from testing_support.settings import redis_multiple_settings

DB_MULTIPLE_SETTINGS = redis_multiple_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]
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

# Operations

def exercise_redis(client):
    client.set('key', 'value')
    client.get('key')

# Tests

@pytest.mark.skipif(six.PY3, reason='Redis Blaster is Python 2 only.')
@pytest.mark.skipif(REDIS_PY_VERSION < (2, 7),
        reason='Redis Blaster requires redis>=2.7')
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_custom_conn_pool:test_redis_blaster_operation_enable_instance',
        scoped_metrics=_base_scoped_metrics,
        rollup_metrics=_base_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_blaster_operation_enable_instance():
    from rb import Cluster

    cluster = Cluster(
            hosts={0: {'port': DB_SETTINGS['port']}},
            host_defaults={'host': DB_SETTINGS['host']}
    )
    client = cluster.get_routing_client()
    exercise_redis(client)

@pytest.mark.skipif(six.PY3, reason='Redis Blaster is Python 2 only.')
@pytest.mark.skipif(REDIS_PY_VERSION < (2, 7),
        reason='Redis Blaster requires redis>=2.7')
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_custom_conn_pool:test_redis_blaster_operation_disable_instance',
        scoped_metrics=_base_scoped_metrics,
        rollup_metrics=_base_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_blaster_operation_disable_instance():
    from rb import Cluster

    cluster = Cluster(
            hosts={0: {'port': DB_SETTINGS['port']}},
            host_defaults={'host': DB_SETTINGS['host']}
    )
    client = cluster.get_routing_client()
    exercise_redis(client)

