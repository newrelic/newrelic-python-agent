import pytest
import redis

from newrelic.agent import background_task

from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings)
from testing_support.settings import redis_multiple_settings
from testing_support.util import instance_hostname

DB_MULTIPLE_SETTINGS = redis_multiple_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]

# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

_base_scoped_metrics = (
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/set', 1),
        ('Datastore/operation/Redis/client_list', 2),
)

_base_rollup_metrics = (
        ('Datastore/all', 4),
        ('Datastore/allOther', 4),
        ('Datastore/Redis/all', 4),
        ('Datastore/Redis/allOther', 4),
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/client_list', 2),
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

def exercise_redis(client):
    client.set('key', 'value')
    client.get('key')

    client.execute_command('CLIENT LIST')
    client.execute_command('CLIENT', 'LIST')

# Tests

@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_redis:test_strict_redis_operation_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_operation_enable_instance():
    client = redis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    exercise_redis(client)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_redis:test_strict_redis_operation_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_operation_disable_instance():
    client = redis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    exercise_redis(client)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_redis:test_redis_operation_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_operation_enable_instance():
    client = redis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    exercise_redis(client)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_redis:test_redis_operation_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_operation_disable_instance():
    client = redis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    exercise_redis(client)


_test_multiple_databases_scoped_metrics = [
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/set', 1),
        ('Datastore/operation/Redis/client_list', 2),
]

_test_multiple_databases_rollup_metrics = [
        ('Datastore/all', 4),
        ('Datastore/allOther', 4),
        ('Datastore/Redis/all', 4),
        ('Datastore/Redis/allOther', 4),
]

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@validate_transaction_metrics('test_redis:test_multiple_datastores',
        scoped_metrics=_test_multiple_databases_scoped_metrics,
        rollup_metrics=_test_multiple_databases_rollup_metrics,
        background_task=True)
@background_task()
def test_multiple_datastores():
    redis1 = DB_MULTIPLE_SETTINGS[0]
    redis2 = DB_MULTIPLE_SETTINGS[1]

    # datastore 1

    r = redis.StrictRedis(host=redis1['host'], port=redis1['port'], db=0)
    r.set('key', 'value')
    r.get('key')

    # datastore 2

    r = redis.StrictRedis(host=redis2['host'], port=redis2['port'], db=1)
    r.execute_command('CLIENT LIST')
    r.execute_command('CLIENT', 'LIST')
