import pytest

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import (
        validate_span_events)


@pytest.mark.parametrize('span_events_enabled,spans_feature_flag', [
        (True, True),
        (True, False),
        (False, True),
])
def test_span_events(span_events_enabled, spans_feature_flag):

    @function_trace()
    def function():
        pass

    _settings = {
        'span_events.enabled': span_events_enabled,
        'feature_flag': set(['span_events']) if spans_feature_flag else set(),
    }

    count = 0
    if span_events_enabled and spans_feature_flag:
        count = 2  # root span & function traced span

    @validate_span_events(count=count)
    @override_application_settings(_settings)
    @background_task()
    def _test():
        function()

    _test()
