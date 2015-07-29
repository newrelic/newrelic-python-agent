import json
import mock
import os
import pytest

from newrelic.common.utilization import aws_data, requests


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures', 'aws.json'))

_parameters_list = ['testname', 'uris', 'expected_vendors_hash',
        'expected_metrics']

_parameters = ','.join(_parameters_list)

def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)

def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _parameters_list])

_aws_tests = [_parametrize_test(t) for t in _load_tests()]

_metadata_urls = {
    'id_url': 'http://169.254.169.254/2008-02-01/meta-data/instance-id',
    'type_url': 'http://169.254.169.254/2008-02-01/meta-data/instance-type',
    'zone_url': 'http://169.254.169.254/2008-02-01/meta-data/placement/availability-zone',
}

class MockResponse(object):

    def __init__(self, code, body):
        self.code = code
        self.text = body

@pytest.mark.parametrize(_parameters, _aws_tests)
def test_aws(testname, uris, expected_vendors_hash, expected_metrics):

    # Sanity check that the uris in the test match what we expect

    assert sorted(_metadata_urls.values()) == sorted(uris.keys())

    # Generate mock responses for requests.Session.get

    def _get_mock_return_value(api_result):
        if api_result['timeout']:
            return Exception
        else:
            return MockResponse('200', api_result['response'])

    mock_return_values = [_get_mock_return_value(api_result) for api_result in
            (uris[_metadata_urls['id_url']],
             uris[_metadata_urls['type_url']],
             uris[_metadata_urls['zone_url']])]

    # Define function that actually runs the test

    @mock.patch('newrelic.common.utilization.internal_metric')
    @mock.patch.object(requests.Session, 'get')
    def _test_aws_data(mock_get, mock_internal_metric):
        mock_get.side_effect = mock_return_values

        data = aws_data()

        if data:
            aws_vendor_hash = {'aws': data}
        else:
            aws_vendor_hash = None

        assert aws_vendor_hash == expected_vendors_hash

        if expected_metrics:
            item = list(expected_metrics.items())[0]
            key = item[0]
            value = item[1]['call_count']
            mock_internal_metric.assert_called_with(key, value)

    _test_aws_data()
