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
        ('Datastore/operation/Redis/client_list', 1),
)

_base_rollup_metrics = (
        ('Datastore/all', 3),
        ('Datastore/allOther', 3),
        ('Datastore/Redis/all', 3),
        ('Datastore/Redis/allOther', 3),
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/get', 1),
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

def exercise_redis(client_1, client_2):
    client_1.set('key', 'value')
    client_1.get('key')

    client_2.execute_command('CLIENT', 'LIST', parse='LIST')

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics('test_multiple_dbs:test_multiple_datastores_enabled',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_multiple_datastores_enabled():
    redis1 = DB_MULTIPLE_SETTINGS[0]
    redis2 = DB_MULTIPLE_SETTINGS[1]

    client_1 = redis.StrictRedis(host=redis1['host'], port=redis1['port'], db=0)
    client_2 = redis.StrictRedis(host=redis2['host'], port=redis2['port'], db=1)
    exercise_redis(client_1, client_2)

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics('test_multiple_dbs:test_multiple_datastores_disabled',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_multiple_datastores_disabled():
    redis1 = DB_MULTIPLE_SETTINGS[0]
    redis2 = DB_MULTIPLE_SETTINGS[1]

    client_1 = redis.StrictRedis(host=redis1['host'], port=redis1['port'], db=0)
    client_2 = redis.StrictRedis(host=redis2['host'], port=redis2['port'], db=1)
    exercise_redis(client_1, client_2)
