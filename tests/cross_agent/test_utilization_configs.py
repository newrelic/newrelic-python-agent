import pytest
import os
import json

from newrelic.core.data_collector import ApplicationSession
import newrelic.core.config

INITIAL_ENV = os.environ

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE = os.path.normpath(os.path.join(
        CURRENT_DIR, 'fixtures', 'utilization', 'utilization_json.json'))

def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)

class Environ(object):
    def __init__(self, env_dict):
        env_dict = env_dict or {}
        for key, val in env_dict.items():
            env_dict[key] = str(val)
        self.env_dict = env_dict

    def __enter__(self):
        os.environ.update(self.env_dict)

    def __exit__(self, *args, **kwargs):
        os.environ.clear()
        os.environ = INITIAL_ENV

def _mock_aws_data(test):
    def aws_data():
        if test.get('input_aws_id'):
            return {
                'id': test.get('input_aws_id'),
                'type': test.get('input_aws_type'),
                'zone': test.get('input_aws_zone'),
            }
        return {}
    return aws_data

def _mock_logical_processor_count(cnt):
    def logical_processor_count():
        return cnt
    return logical_processor_count

def _mock_total_physical_memory(mem):
    def total_physical_memory():
        return mem
    return total_physical_memory

def _mock_gethostname(name):
    def gethostname():
        return name
    return gethostname

def assert_dicts_equal(dict1, dict2):
    """Assert that all the key, value pairs in dict1 match those found in
    dict2. There can be some keys in dict2 that are not in dict1, but if there
    are keys in dict1 that are not in dict2, return False.

    """
    for key in dict1.keys():
        val1 = dict1.get(key)
        val2 = dict2.get(key)
        if isinstance(val1, dict) and isinstance(val2, dict):
            assert_dicts_equal(val1, val2)
        elif val1 != val2:
            raise AssertionError('For key %s: %s != %s' % (key, val2, val1))

def _update_settings(test):
    """Update the settings dict to reflect the environment variables found in
    the test.

    """
    with Environ(test.get('input_environment_variables')):
        cc = newrelic.core.config
        try:
            cc._settings.utilization.logical_processors = int(os.environ.get(
                'NEW_RELIC_UTILIZATION_LOGICAL_PROCESSORS', 0))
            cc._settings.utilization.total_ram_mib = int(os.environ.get(
                'NEW_RELIC_UTILIZATION_TOTAL_RAM_MIB', 0))
        except ValueError:
            # when a non-number is set as a env var for these, they should just
            # be ignored.
            pass

        cc._settings.utilization.billing_hostname = os.environ.get(
            'NEW_RELIC_UTILIZATION_BILLING_HOSTNAME')


@pytest.mark.parametrize('test', _load_tests())
def test_billing_hostname_from_env_vars(test):
    # mock the methods that derive the data for the payload
    dc = newrelic.core.data_collector
    dc.aws_data = _mock_aws_data(test)
    dc.logical_processor_count = _mock_logical_processor_count(
            test.get('input_logical_processors'))
    dc.total_physical_memory = _mock_total_physical_memory(
            test.get('input_total_ram_mib'))
    dc.socket.gethostname = _mock_gethostname(
            test.get('input_hostname'))

    _update_settings(test)
    settings = newrelic.core.config.global_settings_dump()

    local_config, = ApplicationSession._create_connect_payload(
            '', [], [], settings)
    util_output = local_config['utilization']
    expected_output = test['expected_output_json']
    assert_dicts_equal(expected_output, util_output)
