import pytest
import redis

from newrelic.agent import background_task

from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings)
from testing_support.settings import redis_multiple_settings
from testing_support.util import instance_hostname

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
        (_instance_metric_name, None)
)

_disable_rollup_metrics.append(
        (_instance_metric_name, None)
)

@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_two_args_enable',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_two_args_enable():
    r = redis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    r.execute_command('CLIENT', 'LIST', parse='LIST')

@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_two_args_disabled',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_two_args_disabled():
    r = redis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    r.execute_command('CLIENT', 'LIST', parse='LIST')

@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_redis_execute_command_two_args_enable',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_execute_command_two_args_enable():
    r = redis.Redis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    r.execute_command('CLIENT', 'LIST', parse='LIST')

@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_redis_execute_command_two_args_disabled',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_execute_command_two_args_disabled():
    r = redis.Redis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    r.execute_command('CLIENT', 'LIST', parse='LIST')

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10),
        reason='This command is not implemented yet')
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_as_one_arg_enable',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_as_one_arg_enable():
    r = redis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    r.execute_command('CLIENT LIST')

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10),
        reason='This command is not implemented yet')
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_strict_redis_execute_command_as_one_arg_disabled',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_strict_redis_execute_command_as_one_arg_disabled():
    r = redis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    r.execute_command('CLIENT LIST')

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10),
        reason='This command is not implemented yet')
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_redis_execute_command_as_one_arg_enable',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_execute_command_as_one_arg_enable():
    r = redis.Redis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    r.execute_command('CLIENT LIST')

@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10),
        reason='This command is not implemented yet')
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_execute_command:test_redis_execute_command_as_one_arg_disabled',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@background_task()
def test_redis_execute_command_as_one_arg_disabled():
    r = redis.Redis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=0)
    r.execute_command('CLIENT LIST')
