import json
import webtest
import pytest

from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.wsgi_application import wsgi_application
from testing_support.fixtures import (override_application_settings,
        validate_transaction_event_attributes, validate_transaction_metrics)
from testing_support.validators.validate_span_events import (
    validate_span_events)


@wsgi_application()
def target_wsgi_application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'application/json')])
    txn = current_transaction()
    txn._sampled = True
    headers = ExternalTrace.generate_request_headers(txn)
    return [json.dumps(headers).encode('utf-8')]


test_application = webtest.TestApp(target_wsgi_application)


_override_settings = {
    'trusted_account_key': '1',
    'distributed_tracing.enabled': True,
    'distributed_tracing.format': 'w3c',
}


INBOUND_TRACEPARENT_ZERO_PARENT_ID = \
        '00-0af7651916cd43dd8448eb211c80319c-0000000000000000-01'
INBOUND_TRACEPARENT_ZERO_TRACE_ID = \
        '00-00000000000000000000000000000000-00f067aa0ba902b7-01'
INBOUND_TRACEPARENT = \
        '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
INBOUND_TRACESTATE = \
        'rojo=00f067aa0ba902b7,congo=t61rcWkgMzE'
LONG_TRACESTATE = \
        ','.join(["{}rojo=f06a0ba902b7".format(x) for x in range(32)])
INBOUND_UNTRUSTED_NR_TRACESTATE = \
        '2@nr=0-0-1345936-55632452-27jjj2d8890283b4-b28ce285632jjhl9-'
INBOUND_NR_TRACESTATE = \
        ('1@nr=0-0-1349956-41346604-27ddd2d8890283b4-b28be285632bbc0a-'
        '1-1.1273-1569367663277')

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

_metrics = [("Supportability/TraceContext/Create/Success", 1),
            ("Supportability/TraceContext/TraceParent/Accept/Success", 1)]


@pytest.mark.parametrize('inbound_tracestate,update_tracestate,metrics',
        (('', False, []),
        (INBOUND_TRACESTATE, False, [
            ("Supportability/TraceContext/Accept/Success", 1),
            ("Supportability/TraceContext/TraceState/NoNrEntry", 1)]),
        (INBOUND_NR_TRACESTATE + ',' + INBOUND_TRACESTATE, True,
            [("Supportability/TraceContext/Accept/Success", 1)]),
        (LONG_TRACESTATE + ',' + INBOUND_NR_TRACESTATE, True,
            [("Supportability/TraceContext/Accept/Success", 1)])))
@override_application_settings(_override_settings)
def test_tracestate_is_propagated(
        inbound_tracestate, update_tracestate, metrics):
    headers = {
        'traceparent': INBOUND_TRACEPARENT,
        'tracestate': inbound_tracestate
    }

    metrics.extend(_metrics)

    @validate_transaction_metrics("",
            group="Uri",
            rollup_metrics=metrics)
    def _test():
        return test_application.get('/', headers=headers)

    response = _test()
    for header_name, header_value in response.json:
        if header_name == 'tracestate':
            break
    else:
        assert False, 'tracestate header not propagated'

    tracestate = header_value.split(',')
    assert len(tracestate) <= 32
    nr_header = tracestate[0]
    key, value = nr_header.split('=')
    assert key == '1@nr'
    fields = value.split('-')
    assert len(fields) == 9
    assert fields[0] == '0'
    assert fields[1] == '0'
    # sampled and priority should match the inbound tracestate
    if update_tracestate:
        assert fields[6] == '1'
        assert fields[7] == '1.1273'


expected_metrics_span_events_disabled = [
    ("Supportability/TraceContext/Accept/Success", 1),
    ("Supportability/TraceContext/TraceState/NoNrEntry", 1),
    ("Supportability/TraceContext/Create/Success", 1),
    ("Supportability/TraceContext/TraceParent/Accept/Success", 1)
]


def test_tracestate_span_events_disabled():
    headers = {
        'traceparent': INBOUND_TRACEPARENT,
        'tracestate': INBOUND_TRACESTATE
    }
    settings = _override_settings.copy()
    settings['span_events.enabled'] = False

    @validate_transaction_metrics(name="", group="Uri",
            rollup_metrics=expected_metrics_span_events_disabled)
    @override_application_settings(settings)
    def _test():
        return test_application.get('/', headers=headers)

    response = _test()

    for header_name, header_value in response.json:
        if header_name == 'tracestate':
            break
    else:
        assert False, 'tracestate header not propagated'

    # If span_events are disabled the INBOUND_TRACESTATE should be left as is
    assert header_value == INBOUND_TRACESTATE


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
        return test_application.get('/', headers=headers)

    response = _test()
    for header_name, header_value in response.json:
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
    assert fields[3] in ('00', '01')


@pytest.mark.parametrize('traceparent,intrinsics,metrics', (
    (INBOUND_TRACEPARENT, {
            "traceId": "0af7651916cd43dd8448eb211c80319c",
            "parentSpanId": "00f067aa0ba902b7",
            "parent.transportType": "HTTP"},
            [("Supportability/TraceContext/TraceParent/Accept/Success", 1)]),
    (INBOUND_TRACEPARENT + '-extra-fields', {
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
        test_application.get('/', headers={"traceparent": traceparent})

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

    @validate_span_events(exact_intrinsics=intrinsics)
    def _test():
        test_application.get('/', headers={
            "traceparent": INBOUND_TRACEPARENT,
            "tracestate": tracestate,
        })

    _test()
