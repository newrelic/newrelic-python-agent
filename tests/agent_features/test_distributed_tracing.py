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
import pytest
import webtest
import copy

from newrelic.api.application import application_instance
from newrelic.api.background_task import background_task, BackgroundTask
from newrelic.api.transaction import (current_transaction, current_trace_id,
        current_span_id)
from newrelic.api.time_trace import current_trace
from newrelic.api.web_transaction import WSGIWebTransaction
from newrelic.api.wsgi_application import wsgi_application

from testing_support.fixtures import (override_application_settings,
        validate_attributes, validate_transaction_event_attributes,
        validate_error_event_attributes, validate_transaction_metrics)

distributed_trace_intrinsics = ['guid', 'traceId', 'priority', 'sampled']
inbound_payload_intrinsics = ['parent.type', 'parent.app', 'parent.account',
        'parent.transportType', 'parent.transportDuration']

payload = {
    'v': [0, 1],
    'd': {
        'ac': '1',
        'ap': '2827902',
        'id': '7d3efb1b173fecfa',
        'pa': '5e5733a911cfbc73',
        'pr': 10.001,
        'sa': True,
        'ti': 1518469636035,
        'tr': 'd6b4ba0c3a712ca',
        'ty': 'App',
    }
}
parent_order = ['parent_type', 'parent_account',
                'parent_app', 'parent_transport_type']
parent_info = {
    'parent_type': payload['d']['ty'],
    'parent_account': payload['d']['ac'],
    'parent_app': payload['d']['ap'],
    'parent_transport_type': 'HTTP'
}


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'hello world'
    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]

    txn = current_transaction()

    # Make assertions on the WSGIWebTransaction object
    assert txn._distributed_trace_state
    assert txn.parent_type == 'App'
    assert txn.parent_app == '2827902'
    assert txn.parent_account == '1'
    assert txn.parent_span == '7d3efb1b173fecfa'
    assert txn.parent_transport_type == 'HTTP'
    assert isinstance(txn.parent_transport_duration, float)
    assert txn._trace_id == 'd6b4ba0c3a712ca'
    assert txn.priority == 10.001
    assert txn.sampled

    start_response(status, response_headers)
    return [output]


test_application = webtest.TestApp(target_wsgi_application)

_override_settings = {
    'trusted_account_key': '1',
    'distributed_tracing.enabled': True,
}


_metrics = [
        ('Supportability/DistributedTrace/AcceptPayload/Success', 1),
        ('Supportability/TraceContext/Accept/Success', None)
]


@override_application_settings(_override_settings)
@validate_transaction_metrics(
    '',
    group='Uri',
    rollup_metrics=_metrics)
def test_distributed_tracing_web_transaction():
    headers = {'newrelic': json.dumps(payload)}
    response = test_application.get('/', headers=headers)
    assert 'X-NewRelic-App-Data' not in response.headers


@pytest.mark.parametrize('span_events', (True, False))
@pytest.mark.parametrize('accept_payload', (True, False))
def test_distributed_trace_attributes(span_events, accept_payload):
    if accept_payload:
        _required_intrinsics = (
                distributed_trace_intrinsics + inbound_payload_intrinsics)
        _forgone_txn_intrinsics = []
        _forgone_error_intrinsics = []
        _exact_intrinsics = {
            'parent.type': 'Mobile',
            'parent.app': '2827902',
            'parent.account': '1',
            'parent.transportType': 'HTTP',
            'traceId': 'd6b4ba0c3a712ca',
        }
        _exact_txn_attributes = {'agent': {}, 'user': {},
                'intrinsic': _exact_intrinsics.copy()}
        _exact_error_attributes = {'agent': {}, 'user': {},
                'intrinsic': _exact_intrinsics.copy()}
        _exact_txn_attributes['intrinsic']['parentId'] = '7d3efb1b173fecfa'
        _exact_txn_attributes['intrinsic']['parentSpanId'] = 'c86df80de2e6f51c'

        _forgone_error_intrinsics.append('parentId')
        _forgone_error_intrinsics.append('parentSpanId')
        _forgone_txn_intrinsics.append('grandparentId')
        _forgone_error_intrinsics.append('grandparentId')

        _required_attributes = {
                'intrinsic': _required_intrinsics, 'agent': [], 'user': []}
        _forgone_txn_attributes = {'intrinsic': _forgone_txn_intrinsics,
                'agent': [], 'user': []}
        _forgone_error_attributes = {'intrinsic': _forgone_error_intrinsics,
                'agent': [], 'user': []}
    else:
        _required_intrinsics = distributed_trace_intrinsics
        _forgone_txn_intrinsics = _forgone_error_intrinsics = \
                inbound_payload_intrinsics + ['grandparentId', 'parentId',
                'parentSpanId']

        _required_attributes = {
                'intrinsic': _required_intrinsics, 'agent': [], 'user': []}
        _forgone_txn_attributes = {'intrinsic': _forgone_txn_intrinsics,
                'agent': [], 'user': []}
        _forgone_error_attributes = {'intrinsic': _forgone_error_intrinsics,
                'agent': [], 'user': []}
        _exact_txn_attributes = _exact_error_attributes = None

    _forgone_trace_intrinsics = _forgone_error_intrinsics

    test_settings = _override_settings.copy()
    test_settings['span_events.enabled'] = span_events

    @override_application_settings(test_settings)
    @validate_transaction_event_attributes(
            _required_attributes, _forgone_txn_attributes,
            _exact_txn_attributes)
    @validate_error_event_attributes(
            _required_attributes, _forgone_error_attributes,
            _exact_error_attributes)
    @validate_attributes('intrinsic',
            _required_intrinsics, _forgone_trace_intrinsics)
    @background_task(name='test_distributed_trace_attributes')
    def _test():
        txn = current_transaction()

        payload = {
            "v": [0, 1],
            "d": {
                "ty": "Mobile",
                "ac": "1",
                "ap": "2827902",
                "id": "c86df80de2e6f51c",
                "tr": "d6b4ba0c3a712ca",
                "ti": 1518469636035,
                "tx": "7d3efb1b173fecfa"
            }
        }
        payload['d']['pa'] = "5e5733a911cfbc73"

        if accept_payload:
            result = txn.accept_distributed_trace_payload(payload)
            assert result
        else:
            txn._create_distributed_trace_payload()

        try:
            raise ValueError('cookies')
        except ValueError:
            txn.notice_error()

    _test()


_forgone_attributes = {
    'agent': [],
    'user': [],
    'intrinsic': (inbound_payload_intrinsics + ['grandparentId']),
}


@override_application_settings(_override_settings)
@validate_transaction_event_attributes(
        {}, _forgone_attributes)
@validate_error_event_attributes(
        {}, _forgone_attributes)
@validate_attributes('intrinsic',
        {}, _forgone_attributes['intrinsic'])
@background_task(name='test_distributed_trace_attrs_omitted')
def test_distributed_trace_attrs_omitted():
    txn = current_transaction()
    try:
        raise ValueError('cookies')
    except ValueError:
        txn.notice_error()


# test our distributed_trace metrics by creating a transaction and then forcing
# it to process a distributed trace payload
@pytest.mark.parametrize('web_transaction', (True, False))
@pytest.mark.parametrize('gen_error', (True, False))
@pytest.mark.parametrize('has_parent', (True, False))
def test_distributed_tracing_metrics(web_transaction, gen_error, has_parent):
    def _make_dt_tag(pi):
        return "%s/%s/%s/%s/all" % tuple(pi[x] for x in parent_order)

    # figure out which metrics we'll see based on the test params
    # note: we'll always see DurationByCaller if the distributed
    # tracing flag is turned on
    metrics = ['DurationByCaller']
    if gen_error:
        metrics.append('ErrorsByCaller')
    if has_parent:
        metrics.append('TransportDuration')

    tag = None
    dt_payload = copy.deepcopy(payload)

    # if has_parent is True, our metric name will be info about the parent,
    # otherwise it is Unknown/Unknown/Unknown/Unknown
    if has_parent:
        tag = _make_dt_tag(parent_info)
    else:
        tag = _make_dt_tag(dict((x, 'Unknown') for x in parent_info.keys()))
        del dt_payload['d']['tr']

    # now run the test
    transaction_name = "test_dt_metrics_%s" % '_'.join(metrics)
    _rollup_metrics = [
        ("%s/%s%s" % (x, tag, bt), 1)
        for x in metrics
        for bt in ['', 'Web' if web_transaction else 'Other']
    ]

    def _make_test_transaction():
        application = application_instance()

        if not web_transaction:
            return BackgroundTask(application, transaction_name)

        environ = {'REQUEST_URI': '/trace_ends_after_txn'}
        tn = WSGIWebTransaction(application, environ)
        tn.set_transaction_name(transaction_name)
        return tn

    @override_application_settings(_override_settings)
    @validate_transaction_metrics(
        transaction_name,
        background_task=not(web_transaction),
        rollup_metrics=_rollup_metrics)
    def _test():
        with _make_test_transaction() as transaction:
            transaction.accept_distributed_trace_payload(dt_payload)

            if gen_error:
                try:
                    1 / 0
                except ZeroDivisionError:
                    transaction.notice_error()

    _test()


NEW_RELIC_ACCEPTED = \
        [('Supportability/DistributedTrace/AcceptPayload/Success', 1),
         ('Supportability/TraceContext/Accept/Success', None),
         ('Supportability/TraceContext/TraceParent/Accept/Success', None),
         ('Supportability/TraceContext/Accept/Success', None)]
TRACE_CONTEXT_ACCEPTED = \
        [('Supportability/TraceContext/Accept/Success', 1),
         ('Supportability/TraceContext/TraceParent/Accept/Success', 1),
         ('Supportability/TraceContext/Accept/Success', 1),
         ('Supportability/DistributedTrace/AcceptPayload/Success', None)]
NO_HEADERS_ACCEPTED = \
        [('Supportability/DistributedTrace/AcceptPayload/Success', None),
        ('Supportability/TraceContext/Accept/Success', None),
        ('Supportability/TraceContext/TraceParent/Accept/Success', None),
        ('Supportability/TraceContext/Accept/Success', None)]
TRACEPARENT = '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
TRACESTATE = 'rojo=f06a0ba902b7,congo=t61rcWkgMzE'


@pytest.mark.parametrize('traceparent,tracestate,newrelic,metrics',
                         [(False, False, False, NO_HEADERS_ACCEPTED),
                          (False, False, True, NEW_RELIC_ACCEPTED),
                          (False, True, True, NEW_RELIC_ACCEPTED),
                          (False, True, False, NO_HEADERS_ACCEPTED),
                          (True, True, True, TRACE_CONTEXT_ACCEPTED),
                          (True, False, False, TRACE_CONTEXT_ACCEPTED),
                          (True, False, True, TRACE_CONTEXT_ACCEPTED),
                          (True, True, False, TRACE_CONTEXT_ACCEPTED)]
                         )
@override_application_settings(_override_settings)
def test_distributed_tracing_backwards_compatibility(traceparent,
                                                     tracestate,
                                                     newrelic,
                                                     metrics):

    headers = []
    if traceparent:
        headers.append(('traceparent', TRACEPARENT))
    if tracestate:
        headers.append(('tracestate', TRACESTATE))
    if newrelic:
        headers.append(('newrelic', json.dumps(payload)))

    @validate_transaction_metrics(
        "test_distributed_tracing_backwards_compatibility",
        background_task=True,
        rollup_metrics=metrics)
    @background_task(name='test_distributed_tracing_backwards_compatibility')
    def _test():
        transaction = current_transaction()
        transaction.accept_distributed_trace_headers(headers)

    _test()


@background_task(name='test_current_trace_id_api_inside_transaction')
def test_current_trace_id_api_inside_transaction():
    trace_id = current_trace_id()
    assert len(trace_id) == 32
    assert trace_id == current_transaction().trace_id


def test_current_trace_id_api_outside_transaction():
    trace_id = current_trace_id()
    assert trace_id is None


@background_task(name='test_current_span_id_api_inside_transaction')
def test_current_span_id_inside_transaction():
    span_id = current_span_id()
    assert span_id == current_trace().guid


def test_current_span_id_outside_transaction():
    span_id = current_span_id()
    assert span_id is None
