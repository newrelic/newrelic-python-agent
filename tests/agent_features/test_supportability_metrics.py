import pytest
import subprocess
import sys

import newrelic.agent

from newrelic.core.agent import agent_instance

from testing_support.fixtures import validate_transaction_metrics
from testing_support.validators.validate_metric_payload import (
        validate_metric_payload)


_unscoped_metrics = [
        ('Supportability/api/FunctionTrace', 1),
        ('Supportability/api/current_transaction', 1),
        ('Supportability/api/callable_name', 1),
        ('Supportability/api/background_task', None),
]


@validate_transaction_metrics(
        'test_supportability_metrics:test_apis_in_transaction',
        custom_metrics=_unscoped_metrics,
        background_task=True)
@newrelic.agent.background_task()
def test_apis_in_transaction():
    transaction = newrelic.agent.current_transaction()
    name = newrelic.agent.callable_name(test_apis_in_transaction)
    with newrelic.agent.FunctionTrace(transaction, name):
        pass


_unscoped_metrics = [
        ('Supportability/api/global_settings', 2),
        ('Supportability/api/background_task', None),
]


@validate_transaction_metrics(
        'test_supportability_metrics:test_uses_api_twice',
        custom_metrics=_unscoped_metrics,
        background_task=True)
@newrelic.agent.background_task()
def test_uses_api_twice():
    newrelic.agent.global_settings()
    newrelic.agent.global_settings()


_unscoped_metrics = [
        ('Supportability/api/record_exception', 1),
        ('Supportability/api/background_task', None),
]


@validate_transaction_metrics(
        'test_supportability_metrics:test_record_exception',
        custom_metrics=_unscoped_metrics,
        background_task=True)
@newrelic.agent.background_task()
def test_record_exception():
    try:
        1 / 0
    except ZeroDivisionError:
        newrelic.agent.record_exception(sys.exc_info())


_unscoped_metrics = [
        ('Supportability/api/end_of_transaction', 1),
        ('Supportability/api/function_trace', None),
        ('Supportability/api/background_task', None),
]


@validate_transaction_metrics(
        'test_supportability_metrics:test_end_of_transaction',
        custom_metrics=_unscoped_metrics,
        background_task=True)
@newrelic.agent.background_task()
def test_end_of_transaction():
    # test that even if the transaction is ignored that we still create the
    # metric
    newrelic.agent.end_of_transaction()

    # in this case since there is no longer a transaction, the function_trace
    # metric should not be created here
    @newrelic.agent.function_trace()
    def _nothing():
        pass


@pytest.mark.parametrize('correct_order', [True, False])
def test_import_order_supportability_metrics(correct_order):
    settings = newrelic.agent.global_settings()
    cmd = ['python', 'uninstrumented_tester.py', '--correct-order',
            str(correct_order), '--license-key', settings.license_key,
            '--host', settings.host]
    returncode = subprocess.call(cmd)
    assert returncode == 0


@validate_metric_payload(metrics=[
        ('Supportability/Python/Uninstrumented', None),
])
def test_uninstrumented_none():
    # tests a bug that returned "TypeError: 'NoneType' object is not iterable"
    app_name = 'Python Agent Test (uninstrumented 3)'
    agent = agent_instance()
    agent.activate_application(app_name)
    application = agent._applications.get(app_name)
    application.harvest()
