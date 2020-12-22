# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

_sorting_tests = [
    ('lexicographic', ('a', 1, True), ('ab', 1, True)),
    ('is_include', ('a', 1, True), ('a', 1, False)),
    ('wildcard', ('a*', 1, True), ('a', 1, False)),
    ('wildcard same length', ('a*', 1, True), ('ab', 1, False)),
]

@pytest.mark.parametrize('testname, rule1, rule2', _sorting_tests)
def test_attribute_filter_rule_sort(testname, rule1, rule2):
    first = af.AttributeFilterRule(*rule1)
    second = af.AttributeFilterRule(*rule2)

    assert first < second
    assert first <= second
    assert second > first
    assert second >= first
    assert first != second

_equality_tests = [
    ('is_include', ('a', 1, True), ('a', 1, True)),
    ('not is_include', ('a', 1, False), ('a', 1, False)),
    ('is_wildcard', ('a*', 1, True), ('a*', 1, True)),
]
@pytest.mark.parametrize('testname, rule1, rule2', _equality_tests)
def test_attribute_filter_rule_equality(testname, rule1, rule2):
    first = af.AttributeFilterRule(*rule1)
    second = af.AttributeFilterRule(*rule2)

    assert first == second
