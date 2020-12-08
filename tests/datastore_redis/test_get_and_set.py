import redis

from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings)
from testing_support.db_settings import redis_settings
from testing_support.util import instance_hostname

DB_SETTINGS = redis_settings()[0]

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

def exercise_redis(client):
    client.set('key', 'value')
    client.get('key')

# Tests

@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_get_and_set:test_strict_redis_operation_enable_instance',
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
        'test_get_and_set:test_strict_redis_operation_disable_instance',
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
        'test_get_and_set:test_redis_operation_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_operation_enable_instance():
    client = redis.Redis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    exercise_redis(client)

@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_get_and_set:test_redis_operation_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_operation_disable_instance():
    client = redis.Redis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    exercise_redis(client)
