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

from newrelic.common.utilization import BootIdUtilization

from testing_support.fixtures import validate_internal_metrics


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
SYS_PLATFORM = sys.platform
FIXTURE = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures', 'utilization',
    'boot_id.json'))

_parameters_list = ['testname', 'input_total_ram_mib',
        'input_logical_processors', 'input_hostname', 'input_boot_id',
        'expected_output_json', 'expected_metrics']

_parameters = ','.join(_parameters_list)


def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)


def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _parameters_list])


_boot_id_tests = [_parametrize_test(t) for t in _load_tests()]


class MockedBootIdEndpoint(object):
    def __init__(self, boot_id):
        self.boot_id = boot_id

    def __enter__(self):
        if self.boot_id is not None:
            self.boot_id_file = tempfile.NamedTemporaryFile()
            self.boot_id_file.write(self.boot_id.encode('utf8'))
            self.boot_id_file.seek(0)
            BootIdUtilization.METADATA_URL = self.boot_id_file.name
        else:
            BootIdUtilization.METADATA_URL = '/file/does/not/exist/I/hope'
        sys.platform = 'linux-mock-testing'  # ensure boot_id is gathered

    def __exit__(self, *args, **kwargs):
        sys.platform = SYS_PLATFORM
        if self.boot_id:
            del self.boot_id_file  # close and thus delete the tempfile


@pytest.mark.parametrize(_parameters, _boot_id_tests)
def test_boot_id(testname, input_total_ram_mib, input_logical_processors,
        input_hostname, input_boot_id, expected_output_json, expected_metrics):

    metrics = []
    if expected_metrics:
        metrics = [(k, v.get('call_count')) for k, v in
                expected_metrics.items()]

    @validate_internal_metrics(metrics=metrics)
    def _test_boot_id_data():
        data = BootIdUtilization.detect()

        assert data == expected_output_json.get('boot_id')

    with MockedBootIdEndpoint(input_boot_id):
        _test_boot_id_data()
