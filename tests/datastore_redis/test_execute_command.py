import os

import pytest
import redis

from testing_support.fixtures import validate_transaction_metrics

from newrelic.agent import background_task

REDIS_HOST = os.environ.get('TDIUM_REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('TDIUM_REDIS_PORT', '6379'))

REDIS_HOST = os.environ.get('REDIS_PORT_6379_TCP_ADDR', REDIS_HOST)
REDIS_PORT = int(os.environ.get('REDIS_PORT_6379_TCP_PORT', REDIS_PORT))

REDIS_PY_VERSION = redis.VERSION

_test_execute_command_scoped_metrics = [
        ('Datastore/operation/Redis/client_list', 1),
]

_test_execute_command_rollup_metrics = [
        ('Datastore/all', 1),
        ('Datastore/allOther', 1),
        ('Datastore/Redis/all', 1),
        ('Datastore/Redis/allOther', 1),
        ('Datastore/operation/Redis/client_list', 1),
]

@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_two_args',
        scoped_metrics=_test_execute_command_scoped_metrics,
        rollup_metrics=_test_execute_command_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_two_args():
    r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)

    r.execute_command('CLIENT', 'LIST', parse='LIST')

@validate_transaction_metrics(
        'test_execute_command:test_redis_execute_command_two_args',
        scoped_metrics=_test_execute_command_scoped_metrics,
        rollup_metrics=_test_execute_command_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_execute_command_two_args():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

    r.execute_command('CLIENT', 'LIST', parse='LIST')

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10),
        reason='This command is not implemented yet')
@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_as_one_arg',
        scoped_metrics=_test_execute_command_scoped_metrics,
        rollup_metrics=_test_execute_command_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_as_one_arg():
    r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)

    r.execute_command('CLIENT LIST')

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10),
        reason='This command is not implemented yet')
@validate_transaction_metrics(
        'test_execute_command:test_redis_execute_command_as_one_arg',
        scoped_metrics=_test_execute_command_scoped_metrics,
        rollup_metrics=_test_execute_command_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_execute_command_as_one_arg():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

    r.execute_command('CLIENT LIST')
