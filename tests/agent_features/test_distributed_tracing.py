import json
import pytest
import webtest

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import wsgi_application

from testing_support.fixtures import (override_application_settings,
        validate_attributes, validate_transaction_event_attributes,
        validate_error_event_attributes)

distributed_trace_intrinsics = ['guid', 'nr.tripId', 'traceId', 'priority',
        'sampled']
inbound_payload_intrinsics = ['parent.type', 'parent.app', 'parent.account',
        'parent.transportType', 'parent.transportDuration', 'parentId']

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


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'hello world'
    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]

    txn = current_transaction()

    # Make assertions on the WebTransaction object
    assert txn.is_distributed_trace
    assert txn.parent_type == 'App'
    assert txn.parent_app == '2827902'
    assert txn.parent_account == '1'
    assert txn.parent_transport_type == 'http'
    assert isinstance(txn.parent_transport_duration, float)
    assert txn._trace_id == 'd6b4ba0c3a712ca'
    assert txn.priority == 10.001
    assert txn.sampled
    assert txn.grandparent_id == '5e5733a911cfbc73'
    assert txn.parent_id == '7d3efb1b173fecfa'

    start_response(status, response_headers)
    return [output]


test_application = webtest.TestApp(target_wsgi_application)

_override_settings = {
    'trusted_account_ids': [1, 332029],
    'feature_flag': set(['distributed_tracing']),
}


@override_application_settings(_override_settings)
def test_distributed_tracing_web_transaction():
    headers = {'X-NewRelic-Trace': json.dumps(payload)}

    response = test_application.get('/', headers=headers)
    assert 'X-NewRelic-App-Data' not in response.headers


@pytest.mark.parametrize('accept_payload,has_grandparent', [
    (True, True),
    (True, False),
    (False, False),
])
def test_distributed_trace_attributes(accept_payload, has_grandparent):
    if accept_payload:
        _required_intrinsics = (
                distributed_trace_intrinsics + inbound_payload_intrinsics)
        _forgone_intrinsics = []
        _exact_attributes = {'agent': {}, 'user': {}, 'intrinsic': {
            'parent.type': 'Mobile',
            'parent.app': '2827902',
            'parent.account': '332029',
            'parent.transportType': 'http',
            'parentId': '7d3efb1b173fecfa',
            'traceId': 'd6b4ba0c3a712ca',
        }}
        if has_grandparent:
            _required_intrinsics.append('grandparentId')
            _exact_attributes['grandparentId'] = '5e5733a911cfbc73'
        else:
            _forgone_intrinsics.append('grandparentId')

        _required_attributes = {
                'intrinsic': _required_intrinsics, 'agent': [], 'user': []}
        _forgone_attributes = {'intrinsic': [], 'agent': [], 'user': []}
    else:
        _required_intrinsics = distributed_trace_intrinsics
        _forgone_intrinsics = inbound_payload_intrinsics + ['grandparentId']

        _required_attributes = {
                'intrinsic': _required_intrinsics, 'agent': [], 'user': []}
        _forgone_attributes = {
                'intrinsic': _forgone_intrinsics, 'agent': [], 'user': []}
        _exact_attributes = None

    @override_application_settings(_override_settings)
    @validate_transaction_event_attributes(
            _required_attributes, _forgone_attributes, _exact_attributes)
    @validate_error_event_attributes(
            _required_attributes, _forgone_attributes, _exact_attributes)
    @validate_attributes('intrinsic',
            _required_intrinsics, _forgone_intrinsics)
    @background_task(name='test_distributed_trace_attributes')
    def _test():
        txn = current_transaction()

        payload = {
            "v": [0, 1],
            "d": {
                "ty": "Mobile",
                "ac": "332029",
                "ap": "2827902",
                "id": "7d3efb1b173fecfa",
                "tr": "d6b4ba0c3a712ca",
                "ti": 1518469636035
            }
        }
        if has_grandparent:
            payload['d']['pa'] = "5e5733a911cfbc73"

        if accept_payload:
            result = txn.accept_distributed_trace_payload(payload)
            assert result
        else:
            txn.create_distributed_tracing_payload()

        try:
            raise ValueError('cookies')
        except ValueError:
            txn.record_exception()

    _test()


_forgone_attributes = {
    'agent': [],
    'user': [],
    'intrinsic': (inbound_payload_intrinsics +
                  distributed_trace_intrinsics +
                  ['grandparentId']),
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
        txn.record_exception()
