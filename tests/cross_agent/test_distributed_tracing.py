import json
import os
import pytest
import requests
import six
import webtest

from newrelic.api.transaction import current_transaction
from newrelic.api.wsgi_application import wsgi_application
from newrelic.common.object_wrapper import transient_function_wrapper

from testing_support.fixtures import (override_application_settings,
        validate_transaction_metrics, validate_transaction_event_attributes,
        validate_error_event_attributes, validate_attributes)
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'distributed_tracing'))

_parameters_list = ['account_id', 'comment', 'expected_metrics',
        'force_sampled_true', 'inbound_payloads', 'intrinsics',
        'major_version', 'minor_version', 'outbound_payloads',
        'raises_exception', 'span_events_enabled', 'test_name',
        'transport_type', 'trusted_account_key', 'web_transaction']
_parameters = ','.join(_parameters_list)
_expected_test_name_failures = set((
        'spans_disabled_in_child',
        'create_payload',
        'multiple_create_calls',
        'payload_from_trusted_partnership_account',
        'payload_with_untrusted_key',
        'payload_from_untrusted_account',
        'payload_has_larger_major_version',
        'null_payload',
        'payload_missing_version',
        'payload_missing_data',
        'payload_missing_account',
        'payload_missing_application',
        'payload_missing_type',
        'payload_missing_transactionId_or_guid',
        'payload_missing_traceId',
        'payload_missing_timestamp',
))


def load_tests():
    result = []
    path = os.path.join(JSON_DIR, 'distributed_tracing.json')
    with open(path, 'r') as fh:
        tests = json.load(fh)

    for test in tests:
        values = (test.get(param, None) for param in _parameters_list)
        kwargs = {}
        if test.get('test_name') in _expected_test_name_failures:
            kwargs['marks'] = pytest.mark.xfail(
                    reason='test hasnot been fixed yet', strict=True)
        param = pytest.param(*values, id=test.get('test_name'), **kwargs)
        result.append(param)

    return result


def capture_outbound_payloads(payloads):
    @transient_function_wrapper('newrelic.api.transaction',
            'Transaction.create_distributed_tracing_payload')
    def _capture_payloads(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)
        payloads.append(result)
        return result

    return _capture_payloads


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'hello world'
    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]

    txn = current_transaction()
    txn.set_transaction_name(test_settings['test_name'])

    if not test_settings['web_transaction']:
        txn.background_task = True

    if test_settings['raises_exception']:
        try:
            1 / 0
        except ZeroDivisionError:
            txn.record_exception()

    inbound_payloads = test_settings['inbound_payloads']
    if len(inbound_payloads) == 2:
        result = txn.accept_distributed_trace_payload(inbound_payloads[1],
                test_settings['transport_type'])
        # If the first of the two payloads was falsey,
        # accept_distributed_trace_payload was never called and therefore this
        # one should succeed
        assert not inbound_payloads[0] is result
    elif not inbound_payloads:
        # WebTransaction will not call accept_distributed_trace_payload when
        # the payload is falsey. Therefore, we must call it directly here.
        result = txn.accept_distributed_trace_payload(inbound_payloads)
        assert not result

    outbound_payloads = test_settings['outbound_payloads']
    if outbound_payloads:
        payloads = []

        @capture_outbound_payloads(payloads)
        def make_outbound_request():
            resp = requests.get('http://localhost:%d' % external.port)
            assert resp.status_code == 200

            assert b'X-NewRelic-ID' not in resp.content
            assert b'X-NewRelic-Transaction' not in resp.content
            assert b'newrelic' in resp.content

        with MockExternalHTTPHResponseHeadersServer() as external:
            for expected_payload_d in outbound_payloads:
                make_outbound_request()

                assert payloads
                actual_payload = payloads.pop()
                data = actual_payload['d']
                for key, value in six.iteritems(expected_payload_d):
                    assert data.get(key) == value

    start_response(status, response_headers)
    return [output]


test_application = webtest.TestApp(target_wsgi_application)


@pytest.mark.parametrize(_parameters, load_tests())
def test_distributed_tracing(account_id, comment, expected_metrics,
        force_sampled_true, inbound_payloads, intrinsics, major_version,
        minor_version, outbound_payloads, raises_exception,
        span_events_enabled, test_name, transport_type, trusted_account_key,
        web_transaction):

    global test_settings
    test_settings = {
        'test_name': test_name,
        'web_transaction': web_transaction,
        'raises_exception': raises_exception,
        'inbound_payloads': inbound_payloads,
        'outbound_payloads': outbound_payloads,
        'transport_type': transport_type,
    }

    override_settings = {
        'distributed_tracing.enabled': True,
        'trusted_account_key': trusted_account_key
    }

    common_required = intrinsics['common']['expected']
    common_forgone = intrinsics['common']['unexpected']
    common_exact = intrinsics['common'].get('exact', {})

    txn_event_required = {'agent': [], 'user': [],
            'intrinsic': intrinsics['Transaction'].get('expected', [])}
    txn_event_required['intrinsic'].extend(common_required)
    txn_event_forgone = {'agent': [], 'user': [],
            'intrinsic': intrinsics['Transaction'].get('unexpected', [])}
    txn_event_forgone['intrinsic'].extend(common_forgone)
    txn_event_exact = {'agent': {}, 'user': {},
            'intrinsic': intrinsics['Transaction'].get('exact', {})}
    txn_event_exact['intrinsic'].update(common_exact)

    if transport_type != 'HTTP':
        # Since wsgi_application calls accept_distributed_trace_payload
        # automatically with transport_type='HTTP', we must defer this call til
        # we can specify the transport type.
        inbound_payloads.insert(0, [])

    payload = json.dumps(inbound_payloads[0]) if inbound_payloads else ''
    headers = {'newrelic': payload}

    @validate_transaction_metrics(test_name,
            rollup_metrics=expected_metrics,
            background_task=not web_transaction)
    @validate_transaction_event_attributes(
            txn_event_required, txn_event_forgone, txn_event_exact)
    @validate_attributes('intrinsic', common_required, common_forgone)
    def _test():
        response = test_application.get('/', headers=headers)
        assert 'X-NewRelic-App-Data' not in response.headers

    if raises_exception:
        error_event_required = {'agent': [], 'user': [],
                'intrinsic': common_required}
        error_event_forgone = {'agent': [], 'user': [],
                'intrinsic': common_forgone}
        error_event_exact = {'agent': {}, 'user': {},
                'intrinsic': common_exact}
        _test = validate_error_event_attributes(error_event_required,
                error_event_forgone, error_event_exact)(_test)

    _test = override_application_settings(override_settings)(_test)

    _test()
