import json
import mock
import os
import pytest

# FIXME: urllib3
requests = pytest.importorskip('newrelic.packages.requests')
from newrelic.common.utilization import GCPUtilization

from testing_support.fixtures import validate_internal_metrics


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'utilization_vendor_specific', 'gcp.json'))

_parameters_list = ['testname', 'uri', 'expected_vendors_hash',
        'expected_metrics']

_parameters = ','.join(_parameters_list)


def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)


def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _parameters_list])


_gcp_tests = [_parametrize_test(t) for t in _load_tests()]


class MockResponse(object):

    def __init__(self, code, body):
        self.code = code
        self.text = body

    def raise_for_status(self):
        assert str(self.code) == '200'

    def json(self):
        return self.text


@pytest.mark.parametrize(_parameters, _gcp_tests)
def test_gcp(testname, uri, expected_vendors_hash, expected_metrics):

    # Generate mock responses for requests.Session.get

    def _get_mock_return_value(api_result):
        if api_result['timeout']:
            return Exception
        else:
            return MockResponse('200', api_result['response'])

    mock_return_values = (
            _get_mock_return_value(uri[GCPUtilization.METADATA_URL]),)

    metrics = []
    if expected_metrics:
        metrics = [(k, v.get('call_count')) for k, v in
                expected_metrics.items()]

    # Define function that actually runs the test

    @validate_internal_metrics(metrics=metrics)
    @mock.patch.object(requests.Session, 'get')
    def _test_gcp_data(mock_get):
        mock_get.side_effect = mock_return_values

        data = GCPUtilization.detect()

        if data:
            gcp_vendor_hash = {'gcp': data}
        else:
            gcp_vendor_hash = None

        assert gcp_vendor_hash == expected_vendors_hash

    _test_gcp_data()
