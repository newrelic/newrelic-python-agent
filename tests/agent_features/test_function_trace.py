import time

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace

from testing_support.fixtures import (validate_transaction_metrics,
        validate_tt_parenting)


_test_function_trace_default_group_scoped_metrics = [
        ('Function/FunctionTrace', 1)]


@validate_transaction_metrics(
        'test_function_trace:test_function_trace_default_group',
        scoped_metrics=_test_function_trace_default_group_scoped_metrics,
        background_task=True)
@background_task()
def test_function_trace_default_group():
    with FunctionTrace('FunctionTrace'):
        pass


_test_function_trace_valid_override_scoped_metrics = [
        ('Custom/FunctionTrace', 1)]


@validate_transaction_metrics(
        'test_function_trace:test_function_trace_valid_override',
        scoped_metrics=_test_function_trace_valid_override_scoped_metrics,
        background_task=True)
@background_task()
def test_function_trace_valid_override():
    with FunctionTrace('FunctionTrace', group='Custom'):
        pass


_test_function_trace_empty_group_scoped_metrics = [
        ('Function/FunctionTrace', 1)]


@validate_transaction_metrics(
        'test_function_trace:test_function_trace_empty_group',
        scoped_metrics=_test_function_trace_empty_group_scoped_metrics,
        background_task=True)
@background_task()
def test_function_trace_empty_group():
    with FunctionTrace('FunctionTrace', group=''):
        pass


_test_function_trace_leading_slash_on_group_scoped_metrics = [
        ('Function/Group/FunctionTrace', 1)]


@validate_transaction_metrics(
    'test_function_trace:test_function_trace_leading_slash_on_group',
    scoped_metrics=_test_function_trace_leading_slash_on_group_scoped_metrics,
    background_task=True)
@background_task()
def test_function_trace_leading_slash_on_group():
    with FunctionTrace('FunctionTrace', group='/Group'):
        pass


_test_async_trace_overlapping_children_scoped_metrics = [
        ('Function/parent', 1),
        ('Function/child_1', 1),
        ('Function/child_2', 1),
]

_test_async_trace_overlapping_children_parenting = (
        'test_function_trace:test_async_trace_overlapping_children', [
            ('parent', [
                ('child_1', []),
                ('child_2', []),
            ]),
        ]
)


@validate_transaction_metrics(
        'test_function_trace:test_async_trace_overlapping_children',
        scoped_metrics=_test_async_trace_overlapping_children_scoped_metrics,
        background_task=True)
@validate_tt_parenting(_test_async_trace_overlapping_children_parenting)
@background_task()
def test_async_trace_overlapping_children():
    parent_trace = FunctionTrace('parent')

    with parent_trace:
        child_trace_1 = FunctionTrace('child_1', parent=parent_trace)
        child_trace_2 = FunctionTrace('child_2', parent=parent_trace)

        child_trace_1.__enter__()
        child_trace_2.__enter__()
        time.sleep(0.01)
        child_trace_1.__exit__(None, None, None)
        child_trace_2.__exit__(None, None, None)

    assert parent_trace.start_time < child_trace_1.start_time
    assert child_trace_1.start_time < child_trace_2.start_time
    assert child_trace_1.end_time < child_trace_2.end_time
    assert child_trace_2.end_time < parent_trace.end_time


@background_task()
def test_function_trace_settings():
    with FunctionTrace("test_trace") as trace:
        assert trace.settings


def test_function_trace_settings_no_transaction():
    with FunctionTrace("test_trace") as trace:
        assert not trace.settings
