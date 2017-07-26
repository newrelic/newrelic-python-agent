import json
import os
import pytest
import sys
import tempfile

# NOTE: the test_utilization_settings_from_env_vars test mocks several of the
# methods in newrelic.core.data_collector and does not put them back!
from newrelic.core.data_collector import ApplicationSession
from newrelic.common.system_info import BootIdUtilization
import newrelic.core.config

from testing_support.mock_external_http_server import MockExternalHTTPServer

try:
    # python 2.x
    reload
except NameError:
    # python 3.x
    from imp import reload

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


class UpdatedSettings(object):
    def __init__(self, test):
        self.test = test
        self.initial_settings = newrelic.core.config._settings

    def __enter__(self):
        """Update the settings dict to reflect the environment variables found in
        the test.

        """
        env = self.test.get('input_environment_variables', {})

        if self.test.get('input_pcf_guid'):
            env.update({
                'CF_INSTANCE_GUID': self.test.get('input_pcf_guid'),
                'CF_INSTANCE_IP': self.test.get('input_pcf_ip'),
                'MEMORY_LIMIT': self.test.get('input_pcf_mem_limit'),
            })

        self.custom_env = Environ(env)
        self.custom_env.__enter__()

        # clean settings cache and reload env vars
        # Note that reload can at times work in unexpected ways. All that is
        # required here is that the globals (such as
        # newrelic.core.config._settings) be reset.
        #
        # From python docs (2.x and 3.x)
        # "When a module is reloaded, its dictionary (containing the module's
        # global variables) is retained. Redefinitions of names will override
        # the old definitions, so this is generally not a problem."
        reload(newrelic.core.config)
        reload(newrelic.config)

        return newrelic.core.config.global_settings_dump()

    def __exit__(self, *args, **kwargs):
        self.custom_env.__exit__(*args, **kwargs)
        newrelic.core.config._settings = self.initial_settings


def assert_dicts_less_than_or_equal(dict1, dict2):
    """Assert that all the key, value pairs in dict1 match those found in
    dict2. There can be some keys in dict2 that are not in dict1, but if there
    are keys in dict1 that are not in dict2, raise AssertionError.

    """
    for key in dict1.keys():
        val1 = dict1.get(key)
        val2 = dict2.get(key)
        if isinstance(val1, dict) and isinstance(val2, dict):
            assert_dicts_less_than_or_equal(val1, val2)
        elif val1 != val2:
            raise AssertionError('For key %s: %s != %s' % (key, val2, val1))


class MockMetadataEndpoints(object):
    def __init__(self, external, test):
        self.external = external
        self.test = test
        self.boot_id_file = None

    def __enter__(self):
        dc = newrelic.core.data_collector

        # mock metadata urls
        if self.test.get('input_aws_id'):
            MockExternalHTTPServer.RESPONSE = json.dumps({
                'instanceId': self.test.get('input_aws_id'),
                'instanceType': self.test.get('input_aws_type'),
                'availabilityZone': self.test.get('input_aws_zone'),
            }).encode('utf8')
            dc.AWSUtilization.METADATA_URL = (
                    'http://localhost:%s' % self.external.port)
        if self.test.get('input_azure_id'):
            MockExternalHTTPServer.RESPONSE = json.dumps({
                'location': self.test.get('input_azure_location'),
                'name': self.test.get('input_azure_name'),
                'vmId': self.test.get('input_azure_id'),
                'vmSize': self.test.get('input_azure_size'),
            }).encode('utf8')
            dc.AzureUtilization.METADATA_URL = (
                    'http://localhost:%s' % self.external.port)
        if self.test.get('input_gcp_id'):
            MockExternalHTTPServer.RESPONSE = json.dumps({
                'id': self.test.get('input_gcp_id'),
                'machineType': self.test.get('input_gcp_type'),
                'name': self.test.get('input_gcp_name'),
                'zone': self.test.get('input_gcp_zone'),
            }).encode('utf8')
            dc.GCPUtilization.METADATA_URL = (
                    'http://localhost:%s' % self.external.port)
        if self.test.get('input_boot_id'):
            self.boot_id_file = tempfile.NamedTemporaryFile()
            self.boot_id_file.write(self.test.get('input_boot_id'))
            self.boot_id_file.seek(0)
            BootIdUtilization.METADATA_URL = self.boot_id_file.name
            sys.platform = 'linux-mock-testing'  # ensure boot_id is gathered

        # mock the methods that derive the data for the payload
        dc.logical_processor_count = _mock_logical_processor_count(
                self.test.get('input_logical_processors'))
        dc.total_physical_memory = _mock_total_physical_memory(
                self.test.get('input_total_ram_mib'))
        dc.system_info.gethostname = _mock_gethostname(
                self.test.get('input_hostname'))

    def __exit__(self, *args, **kwargs):
        del self.boot_id_file  # close and thus delete the tempfile


@pytest.mark.parametrize('test', _load_tests())
def test_utilization_settings(test):
    with MockExternalHTTPServer() as external:
        with MockMetadataEndpoints(external, test):
            with UpdatedSettings(test) as settings:
                local_config, = ApplicationSession._create_connect_payload(
                        '', [], [], settings)
                util_output = local_config['utilization']
                expected_output = test['expected_output_json']
                # assert x == y does not work when running these tests within a
                # docker container b/c util_output will have extra values not
                # found in expected_output
                assert_dicts_less_than_or_equal(expected_output, util_output)
