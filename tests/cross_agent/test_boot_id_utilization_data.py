import json
import mock
import os
import pytest
import sys
import tempfile

from newrelic.common.system_info import BootIdUtilization


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

    @mock.patch('newrelic.common.utilization_common.internal_metric')
    def _test_boot_id_data(mock_internal_metric):
        data = BootIdUtilization.detect()

        assert data == expected_output_json['boot_id']

        if expected_metrics:
            item = list(expected_metrics.items())[0]
            key = item[0]
            value = item[1]['call_count']
            mock_internal_metric.assert_called_with(key, value)

    with MockedBootIdEndpoint(input_boot_id.encode('utf8')):
        _test_boot_id_data()
