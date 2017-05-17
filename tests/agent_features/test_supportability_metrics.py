import sys

import newrelic.agent

from testing_support.fixtures import validate_transaction_metrics


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
        ('Supportability/api/ignore_transaction', 1),
        ('Supportability/api/function_trace', 1),
        ('Supportability/api/background_task', None),
]


@validate_transaction_metrics(
        'test_supportability_metrics:test_ignore_transaction',
        custom_metrics=_unscoped_metrics,
        background_task=True)
@newrelic.agent.background_task()
def test_ignore_transaction():
    # test that even if the transaction is ignored that we still create the
    # metric
    newrelic.agent.ignore_transaction()

    # now, even though the transaction is ignored, we should still still record
    # this function_trace metric
    @newrelic.agent.function_trace()
    def _nothing():
        pass


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
