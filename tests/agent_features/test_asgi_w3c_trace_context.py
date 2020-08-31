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

from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.asgi_application import asgi_application

from testing_support.asgi_testing import AsgiTest
from testing_support.fixtures import (override_application_settings,
        validate_transaction_event_attributes, validate_transaction_metrics)
from testing_support.validators.validate_span_events import (
    validate_span_events)


@asgi_application()
async def target_asgi_application(scope, receive, send):
    status = '200 OK'
    type = "http.response.start"
    txn = current_transaction()
    if txn._sampled is None:
        txn._sampled = True
        txn._priority = 1.2
    headers = ExternalTrace.generate_request_headers(txn)
    response_headers = []
    for key, value in headers:
        encoded_key = key.encode('utf-8')
        encoded_val = value.encode('utf-8')
        response_headers.append((encoded_key, encoded_val))

    await send({
        "type": type,
        "status": status,
        "headers": response_headers,
    })

    await send({
        "type": "http.response.body",
        "body": b"Hello World",
    })

    return [headers]


test_asgi_application = AsgiTest(target_asgi_application)


_override_settings = {
    'trusted_account_key': '1',
    'account_id': '1',
    'primary_application_id': '2',
    'distributed_tracing.enabled': True,
}


INBOUND_TRACEPARENT_ZERO_PARENT_ID = \
        '00-0af7651916cd43dd8448eb211c80319c-0000000000000000-01'
INBOUND_TRACEPARENT_ZERO_TRACE_ID = \
        '00-00000000000000000000000000000000-00f067aa0ba902b7-01'
INBOUND_TRACEPARENT = \
        '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
INBOUND_TRACEPARENT_NEW_VERSION_EXTRA_FIELDS = \
        '01-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01-extra-field'
INBOUND_TRACEPARENT_VERSION_ZERO_EXTRA_FIELDS = \
        '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01-extra-field'
INBOUND_TRACESTATE = \
        'rojo=f06a0ba902b7,congo=t61rcWkgMzE'
LONG_TRACESTATE = \
        ','.join(["{}@rojo=f06a0ba902b7".format(x) for x in range(32)])
INBOUND_UNTRUSTED_NR_TRACESTATE = \
        ('2@nr=0-0-1345936-55632452-27jjj2d8890283b4-b28ce285632jjhl9-'
        '1-1.1273-1569367663277')
INBOUND_NR_TRACESTATE = \
        ('1@nr=0-0-1349956-41346604-27ddd2d8890283b4-b28be285632bbc0a-'
        '1-1.4-1569367663277')
INBOUND_NR_TRACESTATE_UNSAMPLED = \
        ('1@nr=0-0-1349956-41346604-27ddd2d8890283b4-b28be285632bbc0a-'
        '0-0.4-1569367663277')
INBOUND_NR_TRACESTATE_INVALID_TIMESTAMP = \
        ('1@nr=0-0-1349956-41346604-27ddd2d8890283b4-b28be285632bbc0a-'
        '0-0.4-timestamp')
INBOUND_NR_TRACESTATE_INVALID_PARENT_TYPE = \
        ('1@nr=0-parentType-1349956-41346604-'
         '27ddd2d8890283b4-b28be285632bbc0a-1-1.4-1569367663277')

INBOUND_TRACEPARENT_VERSION_FF = \
        'ff-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
INBOUND_TRACEPARENT_VERSION_TOO_LONG = \
        '000-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
INBOUND_TRACEPARENT_INVALID_TRACE_ID = \
        '00-0aF7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
INBOUND_TRACEPARENT_INVALID_PARENT_ID = \
        '00-0af7651916cd43dd8448eb211c80319c-00f067aa0Ba902b7-01'
INBOUND_TRACEPARENT_INVALID_FLAGS = \
        '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-x1'

_metrics = [("Supportability/TraceContext/Create/Success", 1)]


@pytest.mark.parametrize('inbound_nr_tracestate', (True, False))
@override_application_settings(_override_settings)
def test_tracestate_generation(inbound_nr_tracestate):

    headers = {
        'traceparent': INBOUND_TRACEPARENT,
        'tracestate': (
                INBOUND_NR_TRACESTATE_UNSAMPLED if inbound_nr_tracestate
                else INBOUND_TRACESTATE),
    }

    def _test():
        return test_asgi_application.make_request('GET', '/', headers=headers)

    response = _test()

    for header_name, header_value in response.headers.items():
        if header_name == 'tracestate':
            break
    else:
        assert False, 'tracestate header not propagated'

    header_value = header_value.split(',', 1)[0]
    key, value = header_value.split('=', 2)
    assert key == '1@nr'

    fields = value.split('-')
    assert len(fields) == 9

    assert str(int(fields[8])) == fields[8]
    deterministic_fields = fields[:4] + fields[6:8]
    assert deterministic_fields == [
        '0',
        '0',
        '1',
        '2',
        '0' if inbound_nr_tracestate else '1',
        '0.4' if inbound_nr_tracestate else '1.2',
    ]

    assert len(fields[4]) == 16
    assert len(fields[5]) == 16


@pytest.mark.parametrize('inbound_tracestate,expected', (
    ('', None),
    (INBOUND_NR_TRACESTATE + "," + INBOUND_TRACESTATE, INBOUND_TRACESTATE),
    (INBOUND_TRACESTATE, INBOUND_TRACESTATE),
    (LONG_TRACESTATE + ',' + INBOUND_NR_TRACESTATE,
            ','.join("{}@rojo=f06a0ba902b7".format(x) for x in range(31))),
), ids=(
    'empty_inbound_payload',
    'nr_payload',
    'no_nr_payload',
    'long_payload',
))
@override_application_settings(_override_settings)
def test_tracestate_propagation(inbound_tracestate, expected):
    headers = {
        'traceparent': INBOUND_TRACEPARENT,
        'tracestate': inbound_tracestate
    }
    response = test_asgi_application.make_request('GET', '/', headers=headers)
    for header_name, header_value in response.headers.items():
        if header_name == 'tracestate':
            break
    else:
        assert False, 'tracestate header not propagated'

    assert not header_value.endswith(',')
    if inbound_tracestate:
        _, propagated_tracestate = header_value.split(',', 1)
        assert propagated_tracestate == expected


@pytest.mark.parametrize('inbound_traceparent,span_events_enabled', (
    (True, True),
    (True, False),
    (False, True),
))
def test_traceparent_generation(inbound_traceparent, span_events_enabled):
    settings = _override_settings.copy()
    settings['span_events.enabled'] = span_events_enabled

    headers = {}
    if inbound_traceparent:
        headers['traceparent'] = INBOUND_TRACEPARENT

    @override_application_settings(settings)
    def _test():
        return test_asgi_application.make_request('GET', '/', headers=headers)

    response = _test()
    for header_name, header_value in response.headers.items():
        if header_name == 'traceparent':
            break
    else:
        assert False, 'traceparent header not present'

    assert len(header_value) == 55
    assert header_value.startswith('00-')
    fields = header_value.split('-')
    assert len(fields) == 4
    if inbound_traceparent:
        assert fields[1] == '0af7651916cd43dd8448eb211c80319c'
        assert fields[2] != '00f067aa0ba902b7'
    else:
        assert len(fields[1]) == 32
    assert fields[3] in ('00', '01')


@pytest.mark.parametrize('traceparent,intrinsics,metrics', (
    (INBOUND_TRACEPARENT, {
            "traceId": "0af7651916cd43dd8448eb211c80319c",
            "parentSpanId": "00f067aa0ba902b7",
            "parent.transportType": "HTTP"},
            [("Supportability/TraceContext/TraceParent/Accept/Success", 1)]),
    (INBOUND_TRACEPARENT_NEW_VERSION_EXTRA_FIELDS, {
            "traceId": "0af7651916cd43dd8448eb211c80319c",
            "parentSpanId": "00f067aa0ba902b7",
            "parent.transportType": "HTTP"},
            [("Supportability/TraceContext/TraceParent/Accept/Success", 1)]),
    (INBOUND_TRACEPARENT + ' ', {
            "traceId": "0af7651916cd43dd8448eb211c80319c",
            "parentSpanId": "00f067aa0ba902b7",
            "parent.transportType": "HTTP"},
            [("Supportability/TraceContext/TraceParent/Accept/Success", 1)]),

    ('INVALID', {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    ('xx-0', {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    (INBOUND_TRACEPARENT_VERSION_FF, {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    (INBOUND_TRACEPARENT_VERSION_ZERO_EXTRA_FIELDS, {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    (INBOUND_TRACEPARENT[:-1], {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    ('00-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    (INBOUND_TRACEPARENT_INVALID_TRACE_ID, {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    (INBOUND_TRACEPARENT_INVALID_PARENT_ID, {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    (INBOUND_TRACEPARENT_INVALID_FLAGS, {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    (INBOUND_TRACEPARENT_ZERO_TRACE_ID, {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    (INBOUND_TRACEPARENT_ZERO_PARENT_ID, {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
    (INBOUND_TRACEPARENT_VERSION_TOO_LONG, {},
        [("Supportability/TraceContext/TraceParent/Parse/Exception", 1)]),
))
@override_application_settings(_override_settings)
def test_inbound_traceparent_header(traceparent, intrinsics, metrics):
    exact = {'agent': {}, 'user': {}, 'intrinsic': intrinsics}

    @validate_transaction_event_attributes(exact_attrs=exact)
    @validate_transaction_metrics(
            "", group="Uri", rollup_metrics=metrics)
    def _test():
        test_asgi_application.make_request('GET', '/',
                headers={"traceparent": traceparent})

    _test()


@pytest.mark.parametrize('tracestate,intrinsics', (
    (INBOUND_TRACESTATE,
            {'tracingVendors': 'rojo,congo',
             'parentId': '00f067aa0ba902b7'}),
    (INBOUND_NR_TRACESTATE,
            {'trustedParentId': '27ddd2d8890283b4'}),
    ('garbage', {'parentId': '00f067aa0ba902b7'}),
    (INBOUND_TRACESTATE + ',' + INBOUND_NR_TRACESTATE,
            {'parentId': '00f067aa0ba902b7',
             'trustedParentId': '27ddd2d8890283b4',
             'tracingVendors': 'rojo,congo'}),
    (INBOUND_TRACESTATE + ',' + INBOUND_UNTRUSTED_NR_TRACESTATE,
            {'parentId': '00f067aa0ba902b7',
             'tracingVendors': 'rojo,congo,2@nr'}),
    ('rojo=12345,' + 'v' * 257 + '=x',
            {'tracingVendors': 'rojo'}),
    ('rojo=12345,k=' + 'v' * 257,
            {'tracingVendors': 'rojo'}),
))
@override_application_settings(_override_settings)
def test_inbound_tracestate_header(tracestate, intrinsics):

    nr_entry_count = 1 if '1@nr' not in tracestate else None

    metrics = [
        ('Supportability/TraceContext/TraceState/NoNrEntry', nr_entry_count),
    ]

    @validate_transaction_metrics(
            "", group="Uri", rollup_metrics=metrics)
    @validate_span_events(exact_intrinsics=intrinsics)
    def _test():
        test_asgi_application.make_request('GET', '/', headers={
            "traceparent": INBOUND_TRACEPARENT,
            "tracestate": tracestate,
        })

    _test()


@override_application_settings(_override_settings)
def test_w3c_tracestate_header():

    metrics = [
        ('Supportability/TraceContext/Accept/Success', 1),
    ]

    @validate_transaction_metrics(
        "", group="Uri", rollup_metrics=metrics)
    def _test():
        test_asgi_application.make_request('GET', '/', headers={
            "traceparent": INBOUND_TRACEPARENT,
            "tracestate": INBOUND_TRACESTATE,
        })

    _test()


@pytest.mark.parametrize('tracestate', (
    (INBOUND_NR_TRACESTATE_INVALID_TIMESTAMP),
    (INBOUND_NR_TRACESTATE_INVALID_PARENT_TYPE),
    ))
@override_application_settings(_override_settings)
def test_invalid_inbound_nr_tracestate_header(tracestate):

    metrics = [
        ('Supportability/TraceContext/TraceState/InvalidNrEntry', 1)
    ]

    @validate_transaction_metrics(
        "", group="Uri", rollup_metrics=metrics)
    def _test():
        test_asgi_application.make_request('GET', '/', headers={
            "traceparent": INBOUND_TRACEPARENT,
            "tracestate": tracestate,
        })

    _test()


@pytest.mark.parametrize('exclude_newrelic_header', (True, False))
def test_w3c_and_newrelic_headers_generated(exclude_newrelic_header):

    settings = _override_settings.copy()
    settings['distributed_tracing.exclude_newrelic_header'] = \
            exclude_newrelic_header

    @override_application_settings(settings)
    def _test():
        return test_asgi_application.make_request('GET', '/')

    response = _test()
    traceparent = None
    tracestate = None
    newrelic = None
    for header_name, header_value in response.headers.items():
        if header_name == 'traceparent':
            traceparent = header_value
        elif header_name == 'tracestate':
            tracestate = header_value
        elif header_name == 'newrelic':
            newrelic = header_value

    assert traceparent
    assert tracestate

    if exclude_newrelic_header:
        assert newrelic is None
    else:
        assert newrelic
