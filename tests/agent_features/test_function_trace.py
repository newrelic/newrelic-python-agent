from testing_support.fixtures import validate_transaction_metrics

from newrelic.agent import background_task, FunctionTrace, current_transaction

_test_function_trace_default_group_scoped_metrics = [
        ('Function/FunctionTrace', 1)]

@validate_transaction_metrics(
        'test_function_trace:test_function_trace_default_group',
        scoped_metrics=_test_function_trace_default_group_scoped_metrics,
        background_task=True)
@background_task()
def test_function_trace_default_group():
    transaction = current_transaction()
    with FunctionTrace(transaction, 'FunctionTrace'):
        pass

_test_function_trace_valid_override_scoped_metrics = [
        ('Custom/FunctionTrace', 1)]

@validate_transaction_metrics(
        'test_function_trace:test_function_trace_valid_override',
        scoped_metrics=_test_function_trace_valid_override_scoped_metrics,
        background_task=True)
@background_task()
def test_function_trace_valid_override():
    transaction = current_transaction()
    with FunctionTrace(transaction, 'FunctionTrace', group='Custom'):
        pass

_test_function_trace_empty_group_scoped_metrics = [
        ('Function/FunctionTrace', 1)]

@validate_transaction_metrics(
        'test_function_trace:test_function_trace_empty_group',
        scoped_metrics=_test_function_trace_empty_group_scoped_metrics,
        background_task=True)
@background_task()
def test_function_trace_empty_group():
    transaction = current_transaction()
    with FunctionTrace(transaction, 'FunctionTrace', group=''):
        pass

_test_function_trace_leading_slash_on_group_scoped_metrics = [
        ('Function/Group/FunctionTrace', 1)]

@validate_transaction_metrics(
        'test_function_trace:test_function_trace_leading_slash_on_group',
        scoped_metrics=_test_function_trace_leading_slash_on_group_scoped_metrics,
        background_task=True)
@background_task()
def test_function_trace_leading_slash_on_group():
    transaction = current_transaction()
    with FunctionTrace(transaction, 'FunctionTrace', group='/Group'):
        pass
