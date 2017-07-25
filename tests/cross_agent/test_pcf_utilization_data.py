import json
import mock
import os
import pytest

from newrelic.common.utilization_pivotal import PCFUtilization


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
INITIAL_ENV = os.environ
FIXTURE = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'utilization_vendor_specific', 'pcf.json'))

_parameters_list = ['testname', 'env_vars', 'expected_vendors_hash',
        'expected_metrics']

_parameters = ','.join(_parameters_list)


def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)


def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _parameters_list])


_pcf_tests = [_parametrize_test(t) for t in _load_tests()]


class Environ(object):
    def __init__(self, env_dict):
        env_dict = env_dict or {}
        for key, val in env_dict.items():
            env_dict[key] = val.encode('utf8')
        self.env_dict = env_dict

    def __enter__(self):
        os.environ.update(self.env_dict)

    def __exit__(self, *args, **kwargs):
        os.environ.clear()
        os.environ = INITIAL_ENV


class MockResponse(object):

    def __init__(self, code, body):
        self.code = code
        self.text = body

    def raise_for_status(self):
        assert str(self.code) == '200'

    def json(self):
        return self.text


@pytest.mark.parametrize(_parameters, _pcf_tests)
def test_pcf(testname, env_vars, expected_vendors_hash, expected_metrics):

    # Define function that actually runs the test

    @mock.patch('newrelic.common.utilization_common.internal_metric')
    def _test_pcf_data(mock_internal_metric):

        env_dict = dict([(key, val['response']) for key, val in
            env_vars.items()])

        with Environ(env_dict):
            data = PCFUtilization.detect()

        if data:
            pcf_vendor_hash = {'pcf': data}
        else:
            pcf_vendor_hash = None

        assert pcf_vendor_hash == expected_vendors_hash

        if expected_metrics:
            item = list(expected_metrics.items())[0]
            key = item[0]
            value = item[1]['call_count']
            mock_internal_metric.assert_called_with(key, value)

    _test_pcf_data()
