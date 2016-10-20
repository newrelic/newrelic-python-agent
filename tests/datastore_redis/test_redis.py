import pytest

import redis

from testing_support.fixtures import validate_transaction_metrics
from testing_support.settings import redis_multiple_settings

from newrelic.agent import background_task

DB_MULTIPLE_SETTINGS = redis_multiple_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]

_test_redis_scoped_metrics = [
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/set', 1),
        ('Datastore/operation/Redis/client_list', 2)]

_test_redis_rollup_metrics = [
        ('Datastore/all', 4),
        ('Datastore/allOther', 4),
        ('Datastore/Redis/all', 4),
        ('Datastore/Redis/allOther', 4),
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/client_list', 2)]

@validate_transaction_metrics(
        'test_redis:test_strict_redis_operation',
        scoped_metrics=_test_redis_scoped_metrics,
        rollup_metrics=_test_redis_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_operation():
    r = redis.StrictRedis(host=DB_SETTINGS['host'], port=DB_SETTINGS['port'], db=0)

    r.set('key', 'value')
    r.get('key')

    r.execute_command('CLIENT LIST')
    r.execute_command('CLIENT', 'LIST')

@validate_transaction_metrics(
        'test_redis:test_redis_operation',
        scoped_metrics=_test_redis_scoped_metrics,
        rollup_metrics=_test_redis_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_operation():
    r = redis.Redis(host=DB_SETTINGS['host'], port=DB_SETTINGS['port'], db=0)

    r.set('key', 'value')
    r.get('key')

    r.execute_command('CLIENT LIST')
    r.execute_command('CLIENT', 'LIST')

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
