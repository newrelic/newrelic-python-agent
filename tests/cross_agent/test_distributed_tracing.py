import json
import os
import pytest
import webtest

from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import wsgi_application

from testing_support.fixtures import (override_application_settings,
        validate_transaction_metrics, validate_transaction_event_attributes,
        validate_error_event_attributes, validate_attributes)

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'distributed_tracing'))

_parameters_list = ['test_name', 'inbound_payload', 'trusted_account_ids',
        'exact_intrinsics', 'expected_intrinsics', 'unexpected_intrinsics',
        'expected_metrics']
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


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'hello world'
    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]

    txn = current_transaction()
    txn.set_transaction_name(transaction_name)

    start_response(status, response_headers)
    return [output]


test_application = webtest.TestApp(target_wsgi_application)
transaction_name = None


@pytest.mark.parametrize(_parameters, load_tests())
def test_distributed_tracing(test_name, inbound_payload, trusted_account_ids,
        exact_intrinsics, expected_intrinsics,
        unexpected_intrinsics, expected_metrics):

    global transaction_name
    transaction_name = test_name

    override_settings = {
        'trusted_account_ids': trusted_account_ids,
        'feature_flag': set(['distributed_tracing']),
    }
    required_params = {'agent': [], 'user': [],
            'intrinsic': expected_intrinsics}
    forgone_params = {'agent': [], 'user': [],
            'intrinsic': unexpected_intrinsics}
    exact_attrs = {'agent': {}, 'user': {}, 'intrinsic': exact_intrinsics}

    @override_application_settings(override_settings)
    @validate_transaction_metrics(test_name,
            rollup_metrics=expected_metrics)
    @validate_transaction_event_attributes(
            required_params, forgone_params, exact_attrs)
    @validate_error_event_attributes(
            required_params, forgone_params, exact_attrs)
    @validate_attributes('intrinsic',
            expected_intrinsics, unexpected_intrinsics)
    def _test():
        headers = {'X-NewRelic-Trace': json.dumps(inbound_payload)}
        response = test_application.get('/', headers=headers)
        assert 'X-NewRelic-App-Data' not in response.headers

    _test()
