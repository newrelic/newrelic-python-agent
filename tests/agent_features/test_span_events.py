import pytest

from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import (
        validate_span_events)


@pytest.mark.parametrize(
    'span_events_enabled,spans_feature_flag,txn_sampled', [
        (True, True, True),
        (True, False, True),
        (False, True, True),
        (True, True, False),
])
def test_span_events(span_events_enabled, spans_feature_flag, txn_sampled):
    guid = 'dbb536c53b749e0b'
    sentinel_guid = '0687e0c371ea2c4e'
    function_guid = '482439c52de807ee'
    priority = 0.5

    @function_trace(name='child')
    def child():
        pass

    @function_trace(name='function')
    def function():
        txn = current_transaction()
        txn.current_node.guid = function_guid
        child()

    _settings = {
        'span_events.enabled': span_events_enabled,
        'feature_flag': set(['span_events']) if spans_feature_flag else set(),
    }

    count = 0
    if span_events_enabled and spans_feature_flag and txn_sampled:
        count = 1

    exact_intrinsics_common = {
        'type': 'Span',
        'appLocalRootId': guid,
        'sampled': txn_sampled,
        'priority': priority,
        'category': 'generic',
    }
    expected_intrinsics = ('timestamp', 'duration')

    exact_intrinsics_root = exact_intrinsics_common.copy()
    exact_intrinsics_root['name'] = 'Function/transaction'
    exact_intrinsics_root['parentId'] = guid

    exact_intrinsics_function = exact_intrinsics_common.copy()
    exact_intrinsics_function['name'] = 'Function/function'
    exact_intrinsics_function['parentId'] = sentinel_guid
    exact_intrinsics_function['grandparentId'] = guid

    exact_intrinsics_child = exact_intrinsics_common.copy()
    exact_intrinsics_child['name'] = 'Function/child'
    exact_intrinsics_child['parentId'] = function_guid
    exact_intrinsics_child['grandparentId'] = sentinel_guid

    @validate_span_events(count=count,
            exact_intrinsics=exact_intrinsics_root,
            expected_intrinsics=expected_intrinsics)
    @validate_span_events(count=count,
            exact_intrinsics=exact_intrinsics_function,
            expected_intrinsics=expected_intrinsics)
    @validate_span_events(count=count,
            exact_intrinsics=exact_intrinsics_child,
            expected_intrinsics=expected_intrinsics)
    @override_application_settings(_settings)
    @background_task(name='transaction')
    def _test():
        # Force intrinsics
        txn = current_transaction()
        txn.current_node.guid = sentinel_guid
        txn.guid = guid
        txn._priority = priority
        txn._sampled = txn_sampled

        function()

    _test()
