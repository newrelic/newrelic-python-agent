# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import pytest
import sys
import tempfile


# NOTE: the test_utilization_settings_from_env_vars test mocks several of the
# methods in newrelic.core.data_collector and does not put them back!
from testing_support.mock_http_client import create_client_cls
from newrelic.core.agent_protocol import AgentProtocol
from newrelic.common.utilization import (BootIdUtilization, CommonUtilization)
from newrelic.common.object_wrapper import (function_wrapper)
import newrelic.core.config

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


def _mock_logical_processor_count(cnt):
    def logical_processor_count():
        return cnt
    return logical_processor_count


def _mock_total_physical_memory(mem):
    def total_physical_memory():
        return mem
    return total_physical_memory


def _mock_gethostname(name):
    def gethostname(*args, **kwargs):
        return name
    return gethostname


def _mock_getips(ip_addresses):
    def getips(*args, **kwargs):
        return ip_addresses
    return getips


class UpdatedSettings(object):
    def __init__(self):
        self.initial_settings = newrelic.core.config._settings

    def __enter__(self):
        """Update the settings dict to reflect the environment variables found in
        the test.

        """
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

        return newrelic.core.config.global_settings()

    def __exit__(self, *args, **kwargs):
        newrelic.core.config._settings = self.initial_settings


def _get_response_body_for_test(test):
    if test.get('input_aws_id'):
        return json.dumps({
            'instanceId': test.get('input_aws_id'),
            'instanceType': test.get('input_aws_type'),
            'availabilityZone': test.get('input_aws_zone'),
        }).encode('utf8')
    if test.get('input_azure_id'):
        return json.dumps({
            'location': test.get('input_azure_location'),
            'name': test.get('input_azure_name'),
            'vmId': test.get('input_azure_id'),
            'vmSize': test.get('input_azure_size'),
        }).encode('utf8')
    if test.get('input_gcp_id'):
        return json.dumps({
            'id': test.get('input_gcp_id'),
            'machineType': test.get('input_gcp_type'),
            'name': test.get('input_gcp_name'),
            'zone': test.get('input_gcp_zone'),
        }).encode('utf8')


def patch_boot_id_file(test):
    @function_wrapper
    def _patch_boot_id_file(wrapped, instance, args, kwargs):
        boot_id_file = None
        initial_sys_platform = sys.platform

        if test.get('input_boot_id'):
            boot_id_file = tempfile.NamedTemporaryFile()
            boot_id_file.write(test.get('input_boot_id'))
            boot_id_file.seek(0)
            BootIdUtilization.METADATA_URL = boot_id_file.name
            sys.platform = 'linux-mock-testing'  # ensure boot_id is gathered
        else:
            # do not gather boot_id at all, this will ensure there is nothing
            # extra in the gathered utilizations data
            sys.platform = 'not-linux'

        try:
            return wrapped(*args, **kwargs)
        finally:
            del boot_id_file  # close and thus delete the tempfile
            sys.platform = initial_sys_platform

    return _patch_boot_id_file


def patch_system_info(test, monkeypatch):
    @function_wrapper
    def _patch_system_info(wrapped, instance, args, kwargs):
        sys_info = newrelic.common.system_info

        monkeypatch.setattr(sys_info, "logical_processor_count",
                            _mock_logical_processor_count(
                                test.get('input_logical_processors')))
        monkeypatch.setattr(sys_info, "total_physical_memory",
                            _mock_total_physical_memory(
                                test.get('input_total_ram_mib')))
        monkeypatch.setattr(sys_info, "gethostname",
                            _mock_gethostname(
                                test.get('input_hostname')))
        monkeypatch.setattr(sys_info, "getips",
                            _mock_getips(
                                test.get('input_ip_address')))

        return wrapped(*args, **kwargs)

    return _patch_system_info


@pytest.mark.parametrize('test', _load_tests())
def test_utilization_settings(test, monkeypatch):

    env = test.get('input_environment_variables', {})

    if test.get('input_pcf_guid'):
        env.update({
            'CF_INSTANCE_GUID': test.get('input_pcf_guid'),
            'CF_INSTANCE_IP': test.get('input_pcf_ip'),
            'MEMORY_LIMIT': test.get('input_pcf_mem_limit'),
        })

    for key, val in env.items():
        monkeypatch.setenv(key, val)

    @patch_boot_id_file(test)
    @patch_system_info(test, monkeypatch)
    def _test_utilization_data():

        data = _get_response_body_for_test(test)
        client_cls = create_client_cls(200, data)
        monkeypatch.setattr(CommonUtilization, "CLIENT_CLS", client_cls)

        with UpdatedSettings() as settings:
            # Ignoring docker will ensure that there is nothing extra in the
            # gathered utilization data
            monkeypatch.setattr(settings.utilization, "detect_docker", False)

            local_config, = AgentProtocol._connect_payload(
                    '', [], [], settings)
            util_output = local_config['utilization']
            expected_output = test['expected_output_json']

            # The agent does not record full_hostname and it's not required
            expected_output.pop("full_hostname")

            assert expected_output == util_output

    _test_utilization_data()
