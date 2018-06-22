import json
import os
import pytest
import requests
import six
import webtest

from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import wsgi_application
from newrelic.common.object_wrapper import transient_function_wrapper

from testing_support.fixtures import (override_application_settings,
        validate_transaction_metrics, validate_transaction_event_attributes,
        validate_error_event_attributes, validate_attributes)
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'distributed_tracing'))

_parameters_list = ['test_name', 'inbound_payloads'
        'trusted_account_key', 'exact_intrinsics', 'expected_intrinsics',
        'unexpected_intrinsics', 'expected_metrics', 'background_task',
        'raises_exception', 'feature_flag', 'outbound_payloads_d']
_parameters = ','.join(_parameters_list)


def load_tests():
    result = []
    path = os.path.join(JSON_DIR, 'distributed_tracing.json')
    with open(path, 'r') as fh:
        tests = json.load(fh)

    for test in tests:
        values = (test.get(param, None) for param in _parameters_list)
        param = pytest.param(*values, id=test.get('test_name'))
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

    if test_settings['background_task']:
        txn.background_task = True

    if test_settings['raises_exception']:
        try:
            1 / 0
        except ZeroDivisionError:
            txn.record_exception()

    inbound_payloads = test_settings['inbound_payloads']
    if len(inbound_payloads) == 2:
        result = txn.accept_distributed_trace_payload(inbound_payloads[1])
        assert not result
    elif not inbound_payloads:
        # WebTransaction will not call accept_distributed_trace_payload when
        # the payload is falsey. Therefore, we must call it directly here.
        result = txn.accept_distributed_trace_payload(inbound_payloads)
        assert not result

    outbound_payloads_d = test_settings['outbound_payloads_d']
    feature_flag = test_settings['feature_flag'] is not False
    if outbound_payloads_d:
        payloads = []

        @capture_outbound_payloads(payloads)
        def make_outbound_request():
            resp = requests.get('http://localhost:%d' % external.port)
            assert resp.status_code == 200

            if feature_flag:
                assert b'X-NewRelic-ID' not in resp.content
                assert b'X-NewRelic-Transaction' not in resp.content
                assert b'X-NewRelic-Trace' in resp.content
            else:
                assert b'X-NewRelic-ID' in resp.content
                assert b'X-NewRelic-Transaction' in resp.content
                assert b'X-NewRelic-Trace' not in resp.content

        with MockExternalHTTPHResponseHeadersServer() as external:
            for expected_payload_d in outbound_payloads_d:
                make_outbound_request()

                if feature_flag:
                    assert payloads
                    actual_payload = payloads.pop()
                    data = actual_payload['d']
                    for key, value in six.iteritems(expected_payload_d):
                        assert data.get(key) == value
                else:
                    assert not payloads

    start_response(status, response_headers)
    return [output]


test_application = webtest.TestApp(target_wsgi_application)


@pytest.mark.parametrize(_parameters, load_tests())
def test_distributed_tracing(test_name, inbound_payloads,
        trusted_account_key, exact_intrinsics, expected_intrinsics,
        unexpected_intrinsics, expected_metrics, background_task,
        raises_exception, feature_flag, outbound_payloads_d):

    global test_settings
    test_settings = {
        'test_name': test_name,
        'background_task': background_task,
        'raises_exception': raises_exception,
        'inbound_payloads': inbound_payloads,
        'outbound_payloads_d': outbound_payloads_d,
        'feature_flag': feature_flag,
    }

    override_settings = {
        'trusted_account_key': trusted_account_key
    }
    if feature_flag is not False:
        override_settings['feature_flag'] = set(['distributed_tracing'])

    required_params = {'agent': [], 'user': [],
            'intrinsic': expected_intrinsics}
    forgone_params = {'agent': [], 'user': [],
            'intrinsic': unexpected_intrinsics}
    exact_attrs = {'agent': {}, 'user': {}, 'intrinsic': exact_intrinsics}

    payload = json.dumps(inbound_payloads[0]) if inbound_payloads else ''
    headers = {'X-NewRelic-Trace': payload}

    @validate_transaction_metrics(test_name,
            rollup_metrics=expected_metrics,
            background_task=background_task)
    @validate_transaction_event_attributes(
            required_params, forgone_params, exact_attrs)
    @validate_attributes('intrinsic',
            expected_intrinsics, unexpected_intrinsics)
    def _test():
        response = test_application.get('/', headers=headers)
        assert 'X-NewRelic-App-Data' not in response.headers

    if raises_exception:
        _test = validate_error_event_attributes(
                required_params, forgone_params, exact_attrs)(_test)

    _test = override_application_settings(override_settings)(_test)

    _test()
