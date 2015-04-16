import json
import os
import pytest

from newrelic.core import attribute_filter as af
from newrelic.core.config import global_settings, Settings

from testing_support.fixtures import override_application_settings

def _default_settings():
    return {
        'attributes.enabled': True,
        'transaction_events.attributes.enabled': True,
        'transaction_tracer.attributes.enabled': True,
        'error_collector.attributes.enabled': True,
        'browser_monitoring.attributes.enabled': False,
        'attributes.include': [],
        'attributes.exclude': [],
        'transaction_events.attributes.include': [],
        'transaction_events.attributes.exclude': [],
        'transaction_tracer.attributes.include': [],
        'transaction_tracer.attributes.exclude': [],
        'error_collector.attributes.include': [],
        'error_collector.attributes.exclude': [],
        'browser_monitoring.attributes.include': [],
        'browser_monitoring.attributes.exclude': [],
    }

FIXTURE = os.path.join(os.curdir, 'fixtures', 'attribute_configuration.json')

def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)

_fields = ['testname', 'config', 'input_key', 'input_default_destinations',
           'expected_destinations']

def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _fields])

_attributes_tests = [_parametrize_test(t) for t in _load_tests()]

def destinations_as_int(destinations):
    result = af.DST_NONE
    for d in destinations:
        if d == 'transaction_events':
            result |= af.DST_TRANSACTION_EVENTS
        elif d == 'transaction_tracer':
            result |= af.DST_TRANSACTION_TRACER
        elif d == 'error_collector':
            result |= af.DST_ERROR_COLLECTOR
        elif d == 'browser_monitoring':
            result |= af.DST_BROWSER_MONITORING
    return result

@pytest.mark.parametrize(','.join(_fields), _attributes_tests)
def test_attributes(testname, config, input_key, input_default_destinations,
            expected_destinations):

    settings = _default_settings()
    for k, v in config.items():
        settings[k] = v

    attribute_filter = af.AttributeFilter(settings)
    input_destinations = destinations_as_int(input_default_destinations)

    result = attribute_filter.apply(input_key, input_destinations)
    expected = destinations_as_int(expected_destinations)
    assert result == expected, attribute_filter
