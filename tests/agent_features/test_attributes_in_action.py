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

import pytest
import webtest

from newrelic.api.application import application_instance as application
from newrelic.api.message_transaction import message_transaction
from newrelic.api.transaction import add_custom_parameter
from newrelic.api.time_trace import record_exception
from newrelic.api.wsgi_application import wsgi_application
from newrelic.common.object_names import callable_name

from testing_support.fixtures import (validate_transaction_trace_attributes,
        validate_transaction_error_trace_attributes,
        override_application_settings, validate_transaction_event_attributes,
        validate_browser_attributes, validate_error_event_attributes,
        validate_error_trace_attributes_outside_transaction,
        validate_error_event_attributes_outside_transaction,
        reset_core_stats_engine, validate_attributes, dt_enabled)

from testing_support.validators.validate_span_events import (
        validate_span_events)

try:
    from testing_support.sample_asgi_applications import normal_asgi_application
    from testing_support.asgi_testing import AsgiTest
except SyntaxError:
    normal_asgi_application = None


URL_PARAM = 'some_key'
URL_PARAM2 = 'second_key'
REQUEST_URL = '/?' + URL_PARAM + '=someval&' + URL_PARAM2 + '=anotherval'
REQUEST_HEADERS = [
        ('Accept', '*/*'),
        ('Host', 'foobar'),
        ('User-Agent', 'test_attributes_in_action'),
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', '10'), ]

REQ_PARAMS = ['request.parameters.' + URL_PARAM,
        'request.parameters.' + URL_PARAM2]
DISTRIBUTED_TRACE_ATTRS = ['traceId', 'priority', 'parent.type',
        'parent.app', 'parent.account', 'parent.transportType',
        'parent.transportDuration', 'parentId', 'guid', 'sampled',
        'parentSpanId']

USER_ATTRS = ['puppies', 'sunshine']

TRACE_ERROR_AGENT_KEYS = ['response.status',
        'request.method', 'request.headers.contentType', 'request.uri',
        'request.headers.accept', 'request.headers.contentLength',
        'request.headers.host', 'request.headers.userAgent',
        'response.headers.contentLength', 'response.headers.contentType']

AGENT_KEYS_ALL = TRACE_ERROR_AGENT_KEYS + REQ_PARAMS

TRANS_EVENT_INTRINSICS = ('name', 'duration', 'type', 'timestamp', 'totalTime',
        'error')
TRANS_EVENT_AGENT_KEYS = ['response.status', 'request.method', 'request.uri',
        'request.headers.contentType', 'request.headers.contentLength',
        'response.headers.contentLength', 'response.headers.contentType']

BROWSER_INTRINSIC_KEYS = ["beacon", "errorBeacon", "licenseKey",
        "applicationID", "transactionName", "queueTime", "applicationTime",
        "agent"]
ABSENT_BROWSER_KEYS = ['request.method', 'request.headers.contentType',
        'request.headers.contentLength']

ERROR_EVENT_INTRINSICS = ('type', 'error.class', 'error.message', 'timestamp',
        'transactionName', 'duration')
ERROR_PARAMS = ['ohnoes', ]
ERROR_USER_ATTRS = USER_ATTRS + ERROR_PARAMS


@wsgi_application()
def normal_wsgi_application(environ, start_response):
    status = '200 OK'

    output = '<html><head>header</head><body><p>RESPONSE</p></body></html>'
    output = output.encode('UTF-8')

    add_custom_parameter(USER_ATTRS[0], 'test_value')
    add_custom_parameter(USER_ATTRS[1], 'test_value')

    response_headers = [('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    try:
        raise ValueError('Transaction had bad value')
    except ValueError:
        record_exception(params={ERROR_PARAMS[0]: 'param-value'})

    return [output]


application_params=[normal_wsgi_application]
if normal_asgi_application:
    application_params.append(normal_asgi_application)


@pytest.fixture(scope="module", params=application_params)
def normal_application(request):
    if request.param is normal_wsgi_application:
        return webtest.TestApp(normal_wsgi_application)
    else:
        return AsgiTest(normal_asgi_application)

# Tests for checking the presence and format of agent attributes.
# Test default settings.

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ERROR_USER_ATTRS, 'intrinsic': ['trip_id']}

_expected_attributes_event = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ERROR_USER_ATTRS, 'intrinsic': ERROR_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': REQ_PARAMS, 'user': [],
        'intrinsic': DISTRIBUTED_TRACE_ATTRS}


@validate_error_event_attributes(_expected_attributes_event,
        _expected_absent_attributes)
@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
def test_error_in_transaction_default_settings(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': ['trip_id']}


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings({})
def test_transaction_trace_default_attribute_settings(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_expected_attributes = {'agent': TRANS_EVENT_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': TRANS_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': REQ_PARAMS,
        'user': [], 'intrinsic': []}


@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings({})
def test_transaction_event_default_attribute_settings(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


@dt_enabled
@validate_span_events(expected_users=_expected_attributes['user'])
def test_root_span_default_attribute_settings(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# Browser monitoring off by default, turn on and check default destinations


_override_settings = {'browser_monitoring.attributes.enabled': True}

_expected_attributes = {'agent': [], 'user': USER_ATTRS,
        'intrinsic': BROWSER_INTRINSIC_KEYS}

_expected_absent_attributes = {'agent': ABSENT_BROWSER_KEYS + REQ_PARAMS}


@validate_browser_attributes(_expected_attributes, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_default_attribute_settings(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test exclude request params.

_override_settings = {
        'error_collector.attributes.exclude': ['request.parameters.*']}

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ERROR_USER_ATTRS, 'intrinsic': ['trip_id']}

_expected_attributes_event = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ERROR_USER_ATTRS, 'intrinsic': ERROR_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': REQ_PARAMS, 'user': [],
        'intrinsic': []}


@validate_error_event_attributes(_expected_attributes_event,
        _expected_absent_attributes)
@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_exclude_request_params(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {
        'transaction_tracer.attributes.exclude': ['request.parameters.*']}

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': ['trip_id']}


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_exclude_request_params(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'capture_params': True,
        'error_collector.attributes.exclude': ['request.parameters.*']}

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': ['trip_id']}

_expected_absent_attributes = {'agent': REQ_PARAMS, 'user': [],
        'intrinsic': []}


@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_capture_params_exclude_request_params(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'capture_params': True,
        'transaction_tracer.attributes.exclude': ['request.parameters.*']}


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_capture_params_exclude_request_params(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test include request params.

_override_settings = {
        'error_collector.attributes.include': ['request.parameters.*']}

_expected_attributes = {'agent': AGENT_KEYS_ALL, 'user': ERROR_USER_ATTRS,
        'intrinsic': ['trip_id']}

_expected_attributes_event = {'agent': AGENT_KEYS_ALL,
        'user': ERROR_USER_ATTRS, 'intrinsic': ERROR_EVENT_INTRINSICS}


@validate_error_event_attributes(_expected_attributes_event)
@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_include_request_params(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {
        'transaction_tracer.attributes.include': ['request.parameters.*']}

_expected_attributes = {'agent': AGENT_KEYS_ALL, 'user': USER_ATTRS,
        'intrinsic': ['trip_id']}


@validate_transaction_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_include_request_params(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {
        'transaction_events.attributes.include': ['request.parameters.*']}


_expected_attributes = {'agent': TRANS_EVENT_AGENT_KEYS + REQ_PARAMS,
        'user': USER_ATTRS, 'intrinsic': TRANS_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': ['wsgi.output.seconds'], 'user': [],
        'intrinsic': []}


@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_include_request_params(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'browser_monitoring.attributes.enabled': True,
        'browser_monitoring.attributes.include': ['request.parameters.*']}

_expected_attributes = {'agent': REQ_PARAMS, 'user': USER_ATTRS,
        'intrinsic': BROWSER_INTRINSIC_KEYS}

_expected_absent_attributes = {'agent': ABSENT_BROWSER_KEYS, 'user': []}


@validate_browser_attributes(_expected_attributes, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_include_request_params(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test include and exclude request parameters.

_override_settings = {
        'error_collector.attributes.include': ['request.parameters.*'],
        'error_collector.attributes.exclude': [
                'request.parameters.' + URL_PARAM2]}

_expected_attributes = {
        'agent': TRACE_ERROR_AGENT_KEYS + ['request.parameters.' + URL_PARAM],
        'user': ERROR_USER_ATTRS, 'intrinsic': ['trip_id']}

_expected_attributes_event = {
        'agent': TRACE_ERROR_AGENT_KEYS + ['request.parameters.' + URL_PARAM],
        'user': ERROR_USER_ATTRS, 'intrinsic': ERROR_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': ['request.parameters.' + URL_PARAM2],
        'user': [], 'intrinsic': []}


@validate_error_event_attributes(_expected_attributes_event,
        _expected_absent_attributes)
@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_include_exclude(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {
    'transaction_tracer.attributes.include': ['request.parameters.*'],
    'transaction_tracer.attributes.exclude': ['request.parameters.' +
        URL_PARAM2]
}

_expected_attributes = {
        'agent': TRACE_ERROR_AGENT_KEYS + ['request.parameters.' + URL_PARAM],
        'user': USER_ATTRS, 'intrinsic': ['trip_id']}


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_include_exclude(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {
        'transaction_events.attributes.include': ['request.parameters.*'],
        'transaction_events.attributes.exclude': ['request.parameters.' +
        URL_PARAM2]}

_expected_attributes = {
        'agent': TRANS_EVENT_AGENT_KEYS + ['request.parameters.' + URL_PARAM],
        'user': USER_ATTRS, 'intrinsic': TRANS_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': ['request.parameters.' + URL_PARAM2],
        'user': [], 'intrinsic': []}


@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_include_exclude(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'browser_monitoring.attributes.enabled': True,
        'browser_monitoring.attributes.include': ['request.parameters.*'],
        'browser_monitoring.attributes.exclude': [
                'request.parameters.' + URL_PARAM2]}

_expected_attributes = {'agent': ['request.parameters.' + URL_PARAM],
        'user': USER_ATTRS, 'intrinsic': BROWSER_INTRINSIC_KEYS}

_expected_absent_attributes = {'agent': ABSENT_BROWSER_KEYS + [
        'request.parameters.' + URL_PARAM2], 'user': []}


@validate_browser_attributes(_expected_attributes, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_include_exclude_request_params(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test exclude user attribute.

_override_settings = {'error_collector.attributes.exclude': ['puppies']}

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ['sunshine', 'ohnoes'], 'intrinsic': ['trip_id']}

_expected_attributes_event = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ['sunshine', 'ohnoes'], 'intrinsic': ERROR_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': REQ_PARAMS, 'user': ['puppies'],
        'intrinsic': []}


@validate_error_event_attributes(_expected_attributes_event,
        _expected_absent_attributes)
@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_exclude_user_attribute(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'transaction_tracer.attributes.exclude': ['puppies']}

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS, 'user': ['sunshine'],
        'intrinsic': ['trip_id']}


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_exclude_user_attribute(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'transaction_events.attributes.exclude': ['puppies']}

_expected_attributes = {'agent': TRANS_EVENT_AGENT_KEYS, 'user': ['sunshine'],
        'intrinsic': TRANS_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': REQ_PARAMS,
        'user': ['puppies'], 'intrinsic': []}


@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_exclude_user_attribute(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'span_events.attributes.exclude': ['puppies']}


@override_application_settings(_override_settings)
@dt_enabled
@validate_span_events(
        expected_users=_expected_attributes['user'],
        unexpected_users=_expected_absent_attributes['user'])
def test_span_event_exclude_user_attribute(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'browser_monitoring.attributes.enabled': True,
        'browser_monitoring.attributes.exclude': ['puppies']}

_expected_attributes = {'agent': [], 'user': ['sunshine'],
        'intrinsic': BROWSER_INTRINSIC_KEYS}

_expected_absent_attributes = {'agent': ABSENT_BROWSER_KEYS + REQ_PARAMS,
        'user': ['puppies']}


@validate_browser_attributes(_expected_attributes, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_exclude_user_attribute(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test exclude agent attribute.

_override_settings = {'attributes.exclude': ['request.*'],
        'attributes.include': ['request.headers.*']}

_expected_attributes = {'agent': ['response.status',
        'request.headers.contentType', 'request.headers.contentLength'],
        'user': ERROR_USER_ATTRS, 'intrinsic': ['trip_id']}

_expected_attributes_event = {'agent': [
        'response.status', 'request.headers.contentType',
        'request.headers.contentLength'], 'user': ERROR_USER_ATTRS,
        'intrinsic': ERROR_EVENT_INTRINSICS}

_expected_absent_attributes = {
        'agent': ['request.method', 'request.uri'] + REQ_PARAMS,
        'user': [], 'intrinsic': []}


@validate_error_event_attributes(_expected_attributes_event,
        _expected_absent_attributes)
@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_exclude_agent_attribute(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_expected_attributes = {'agent': [ 'response.status',
        'request.headers.contentType', 'request.headers.contentLength'],
        'user': USER_ATTRS, 'intrinsic': ['trip_id']}


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_exclude_agent_attribute(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_expected_attributes = {'agent': ['response.status',
        'request.headers.contentType', 'request.headers.contentLength'],
        'user': USER_ATTRS, 'intrinsic': TRANS_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': ['request.method',
        'request.uri'] + REQ_PARAMS, 'user': [],
        'intrinsic': []}


@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_exclude_agent_attribute(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'attributes.exclude': ['request.*'],
        'attributes.include': ['request.headers.*']}

_expected_agent_attributes = ['response.status',
        'request.headers.contentType', 'request.headers.contentLength']

_expected_absent_agent_attributes = ['request.method',
        'request.uri'] + REQ_PARAMS


@override_application_settings(_override_settings)
@dt_enabled
@validate_span_events(
        expected_agents=_expected_agent_attributes,
        unexpected_agents=_expected_absent_agent_attributes)
def test_span_event_exclude_agent_attribute(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# The only agent attributes browser has are request parameters, which are
# tested in the request parameters test cases

# Test capture_params True.

_override_settings = {'capture_params': True}

_expected_attributes = {'agent': AGENT_KEYS_ALL, 'user': ERROR_USER_ATTRS,
        'intrinsic': ['trip_id']}

_expected_attributes_event = {'agent': AGENT_KEYS_ALL,
        'user': ERROR_USER_ATTRS, 'intrinsic': ERROR_EVENT_INTRINSICS}


@validate_error_event_attributes(_expected_attributes_event)
@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_deprecated_capture_params_true(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_expected_attributes = {'agent': AGENT_KEYS_ALL, 'user': USER_ATTRS,
        'intrinsic': ['trip_id']}


@validate_transaction_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_deprecated_capture_params_true(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test capture_params should not affect transaction events or browser.

_expected_attributes = {'agent': TRANS_EVENT_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': TRANS_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': ['wsgi.output.seconds'] + REQ_PARAMS,
        'user': [], 'intrinsic': []}


@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_deprecated_capture_params_true(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'browser_monitoring.attributes.enabled': True,
        'capture_params': True}

_expected_attributes = {'agent': [], 'user': USER_ATTRS,
        'intrinsic': BROWSER_INTRINSIC_KEYS}

_expected_absent_attributes = {'agent': ABSENT_BROWSER_KEYS + REQ_PARAMS,
        'user': []}


@validate_browser_attributes(_expected_attributes, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_deprecated_capture_params_true(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test capture_params False.

_override_settings = {'capture_params': False}

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ERROR_USER_ATTRS, 'intrinsic': ['trip_id']}

_expected_attributes_event = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ERROR_USER_ATTRS, 'intrinsic': ERROR_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': REQ_PARAMS, 'user': [],
        'intrinsic': []}


@validate_error_event_attributes(_expected_attributes_event,
        _expected_absent_attributes)
@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_deprecated_capture_params_false(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': ['trip_id']}


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_deprecated_capture_params_false(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test capture_params should not affect transaction events.

_expected_attributes = {'agent': TRANS_EVENT_AGENT_KEYS,
        'user': USER_ATTRS, 'intrinsic': TRANS_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': ['wsgi.output.seconds'] + REQ_PARAMS,
        'user': [], 'intrinsic': []}


@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_deprecated_capture_params_false(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'browser_monitoring.attributes.enabled': True,
        'capture_params': False}

_expected_attributes = {'agent': [], 'user': USER_ATTRS,
        'intrinsic': BROWSER_INTRINSIC_KEYS}

_expected_absent_attributes = {'agent': ABSENT_BROWSER_KEYS + REQ_PARAMS,
        'user': []}


@validate_browser_attributes(_expected_attributes, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_deprecated_capture_params_false(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test attempt to exclude intrinsic.

_override_settings = {'error_collector.attributes.exclude': ['trip_id']}

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ERROR_USER_ATTRS, 'intrinsic': ['trip_id']}

_expected_attributes_event = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': ERROR_USER_ATTRS, 'intrinsic': ERROR_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': REQ_PARAMS, 'user': [],
        'intrinsic': []}


@validate_error_event_attributes(_expected_attributes_event,
        _expected_absent_attributes)
@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_exclude_intrinsic(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'transaction_tracer.attributes.exclude': ['trip_id']}

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': ['trip_id']}


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_exclude_intrinsic(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'transaction_events.attributes.exclude': [
        'name', 'duration', 'timestamp', 'type']}

_expected_attributes = {'agent': TRANS_EVENT_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': TRANS_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': ['wsgi.output.seconds'] + REQ_PARAMS,
        'user': [], 'intrinsic': []}


@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_exclude_intrinsic(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'browser_monitoring.attributes.enabled': True,
        'browser_monitoring.attributes.exclude': BROWSER_INTRINSIC_KEYS}

_expected_attributes = {'agent': [], 'user': USER_ATTRS,
        'intrinsic': BROWSER_INTRINSIC_KEYS}

_expected_absent_attributes = {'agent': ABSENT_BROWSER_KEYS + REQ_PARAMS,
        'user': []}


@validate_browser_attributes(_expected_attributes, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_exclude_intrinsic(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test attributes off.

_override_settings = {'error_collector.attributes.enabled': False}

_expected_attributes = {'user': [], 'agent': [], 'intrinsic': ['trip_id']}

_expected_attributes_event = {'user': [], 'agent': [],
        'intrinsic': ERROR_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': AGENT_KEYS_ALL,
        'user': ERROR_USER_ATTRS, 'intrinsic': []}


@validate_error_event_attributes(_expected_attributes_event,
        _expected_absent_attributes)
@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_attributes_disabled(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'transaction_tracer.attributes.enabled': False}


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_attributes_disabled(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {'transaction_events.attributes.enabled': False}

_expected_attributes = {'user': [], 'agent': [],
        'intrinsic': TRANS_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': AGENT_KEYS_ALL,
        'user': USER_ATTRS, 'intrinsic': []}


@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_attributes_disabled(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test browser monitoring off by default.

_expected_attributes = {'agent': [], 'user': [],
        'intrinsic': BROWSER_INTRINSIC_KEYS}

_expected_absent_attributes = {'agent': ABSENT_BROWSER_KEYS + REQ_PARAMS,
        'user': USER_ATTRS}


@validate_browser_attributes(_expected_attributes, _expected_absent_attributes)
@override_application_settings({})
def test_browser_attributes_disabled(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test exclude error parameter.

_override_settings = {'error_collector.attributes.exclude': ERROR_PARAMS}

_expected_attributes = {'agent': TRACE_ERROR_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': ['trip_id']}

_expected_attributes_event = {'agent': TRACE_ERROR_AGENT_KEYS,
        'user': USER_ATTRS, 'intrinsic': ERROR_EVENT_INTRINSICS}

_expected_absent_attributes = {'agent': REQ_PARAMS, 'user': ERROR_PARAMS,
        'intrinsic': []}


@validate_error_event_attributes(_expected_attributes_event,
        _expected_absent_attributes)
@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_error_param_excluded(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test browser monitoring disabled.

_override_settings = {'browser_monitoring.enabled': False}

_expected_attributes = {'agent': TRANS_EVENT_AGENT_KEYS, 'user': USER_ATTRS,
        'intrinsic': []}


@validate_transaction_trace_attributes(_expected_attributes)
@validate_transaction_event_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_browser_monitoring_disabled(normal_application):
    normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# Test outside transaction (error traces and events only).

INTRSICS_NO_TRANS = ('type', 'error.class', 'error.message', 'timestamp',
        'transactionName')


class OutsideWithParamsError(Exception):
    pass


OutsideWithParamsError.name = callable_name(OutsideWithParamsError)


_expected_attributes = {'user': ['test_key'], 'agent': [], 'intrinsic': []}

_expected_attributes_event = {'user': ['test_key'], 'agent': [],
        'intrinsic': INTRSICS_NO_TRANS}


@reset_core_stats_engine()
@validate_error_event_attributes_outside_transaction(
        _expected_attributes_event)
@validate_error_trace_attributes_outside_transaction(
        OutsideWithParamsError.name, _expected_attributes)
def test_error_outside_transaction():

    try:
        raise OutsideWithParamsError("Error outside transaction")
    except OutsideWithParamsError:
        application_instance = application()
        application_instance.record_exception(
                params={'test_key': 'test_value'})


class OutsideNoParamsError(Exception):
    pass


OutsideNoParamsError.name = callable_name(OutsideNoParamsError)

_override_settings = {'error_collector.attributes.exclude': ['test_key']}

_expected_attributes = {}

_expected_attributes_event = {'user': [], 'agent': [],
        'intrinsic': INTRSICS_NO_TRANS}

_expected_absent_attributes = {'user': ['test_key'], 'agent': [],
        'intrinsic': []}


@reset_core_stats_engine()
@validate_error_event_attributes_outside_transaction(
        _expected_attributes_event, _expected_absent_attributes)
@validate_error_trace_attributes_outside_transaction(OutsideNoParamsError.name,
        _expected_attributes, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_outside_transaction_excluded_user_param():

    try:
        raise OutsideNoParamsError("Error outside transaction")
    except OutsideNoParamsError:
        application_instance = application()
        application_instance.record_exception(
                params={'test_key': 'test_value'})


# Test routing key agent attribute.

_required_agent_attributes = ['message.routingKey']
_forgone_agent_attributes = []


@validate_attributes('agent', _required_agent_attributes,
        _forgone_agent_attributes)
@message_transaction(library='RabbitMQ', destination_type='Exchange',
        destination_name='x', routing_key='cat.eat.fishies')
def test_routing_key_agent_attribute():
    pass


_required_agent_attributes = []
_forgone_agent_attributes = ['message.routingKey']


@validate_attributes('agent', _required_agent_attributes,
        _forgone_agent_attributes)
@message_transaction(library='RabbitMQ', destination_type='Exchange',
        destination_name='x')
def test_none_type_routing_key_agent_attribute():
    pass
