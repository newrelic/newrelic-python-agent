import os
import pytest

from newrelic.common import system_info
from newrelic.core import data_collector as dc

from newrelic.core.data_collector import ApplicationSession

# Global constants used in tests
AGENT_VERSION = '2.0.0.0'
APP_NAME = 'test_app'
AWS = {'id': 'foo', 'type': 'bar', 'zone': 'baz'}
AZURE = {'location': 'foo', 'name': 'bar', 'vmId': 'baz', 'vmSize': 'boo'}
GCP = {'id': 1, 'machineType': 'trmntr-t1000', 'name': 'arnold', 'zone': 'abc'}
PCF = {'cf_instance_guid': '1', 'cf_instance_ip': '7', 'memory_limit': '0'}
BROWSER_MONITORING_DEBUG = 'debug'
BROWSER_MONITORING_LOADER = 'loader'
CAPTURE_PARAMS = 'capture_params'
DISPLAY_NAME = 'display_name'
BOOT_ID = 'cca356a7d72737f645a10c122ebbe906'
DOCKER = {'id': 'foobar'}
ENVIRONMENT = []
HIGH_SECURITY = True
HOST = "test_host"
LABELS = 'labels'
LINKED_APPS = ['linked_app_1', 'linked_app_2']
MEMORY = 12000.0
PAYLOAD_APP_NAME = [APP_NAME] + LINKED_APPS
PAYLOAD_ID = ','.join(PAYLOAD_APP_NAME)
PID = 123
PROCESSOR_COUNT = 4
RECORD_SQL = 'record_sql'

_backup_methods = {}


# Mock out the calls used to create the connect payload.
def setup_module(module):
    # Mock out the calls used to create the connect payload.
    def gethostname():
        return HOST
    _backup_methods['gethostname'] = system_info.gethostname
    system_info.gethostname = gethostname

    def getpid():
        return PID
    _backup_methods['getpid'] = os.getpid
    os.getpid = getpid

    def logical_processor_cnt():
        return PROCESSOR_COUNT
    _backup_methods['logical_proc_count'] = dc.logical_processor_count
    dc.logical_processor_count = logical_processor_cnt

    def total_physical_memory():
        return MEMORY
    _backup_methods['total_physical_memory'] = dc.total_physical_memory
    dc.total_physical_memory = total_physical_memory

    def _create_detect(cls, data):
        _backup_methods[cls.__name__] = cls

        class Detector(object):
            VENDOR_NAME = cls.VENDOR_NAME

            @staticmethod
            def detect():
                return data
        return Detector

    dc.BootIdUtilization = _create_detect(dc.BootIdUtilization, BOOT_ID)
    dc.AWSUtilization = _create_detect(dc.AWSUtilization, AWS)
    dc.AzureUtilization = _create_detect(dc.AzureUtilization, AZURE)
    dc.GCPUtilization = _create_detect(dc.GCPUtilization, GCP)
    dc.PCFUtilization = _create_detect(dc.PCFUtilization, PCF)
    dc.DockerUtilization = _create_detect(dc.DockerUtilization, DOCKER)

    _backup_methods['version'] = dc.version
    dc.version = AGENT_VERSION


def teardown_module(module):
    system_info.gethostname = _backup_methods['gethostname']
    os.getpid = _backup_methods['getpid']
    dc.logical_processor_count = _backup_methods['logical_proc_count']
    dc.total_physical_memory = _backup_methods['total_physical_memory']
    dc.version = _backup_methods['version']
    dc.BootIdUtilization = _backup_methods['BootIdUtilization']
    dc.AWSUtilization = _backup_methods['AWSUtilization']
    dc.AzureUtilization = _backup_methods['AzureUtilization']
    dc.GCPUtilization = _backup_methods['GCPUtilization']
    dc.PCFUtilization = _backup_methods['PCFUtilization']
    dc.DockerUtilization = _backup_methods['DockerUtilization']


def default_settings():
    return {'browser_monitoring.loader': BROWSER_MONITORING_LOADER,
            'browser_monitoring.debug': BROWSER_MONITORING_DEBUG,
            'capture_params': CAPTURE_PARAMS,
            'transaction_tracer.record_sql': RECORD_SQL,
            'high_security': HIGH_SECURITY,
            'labels': LABELS,
            'process_host.display_name': DISPLAY_NAME,
            'utilization.detect_aws': True,
            'utilization.detect_azure': True,
            'utilization.detect_docker': True,
            'utilization.detect_gcp': True,
            'utilization.detect_pcf': True}


def payload_asserts(payload, with_aws=True, with_gcp=True, with_pcf=True,
        with_azure=True, with_docker=True):
    payload_data = payload[0]
    assert payload_data['agent_version'] == AGENT_VERSION
    assert payload_data['app_name'] == PAYLOAD_APP_NAME
    assert payload_data['display_host'] == DISPLAY_NAME
    assert payload_data['environment'] == ENVIRONMENT
    assert payload_data['high_security'] == HIGH_SECURITY
    assert payload_data['host'] == HOST
    assert payload_data['identifier'] == PAYLOAD_ID
    assert payload_data['labels'] == LABELS
    assert payload_data['language'] == 'python'
    assert payload_data['pid'] == PID
    assert len(payload_data['security_settings']) == 2
    assert payload_data['security_settings']['capture_params'] == \
            CAPTURE_PARAMS
    assert payload_data['security_settings']['transaction_tracer'] == {
            'record_sql': RECORD_SQL}
    assert len(payload_data['settings']) == 2
    assert payload_data['settings']['browser_monitoring.loader'] == (
            BROWSER_MONITORING_LOADER)
    assert payload_data['settings']['browser_monitoring.debug'] == (
            BROWSER_MONITORING_DEBUG)
    utilization_len = 5 + any([with_aws, with_pcf, with_gcp, with_azure,
            with_docker])
    assert len(payload_data['utilization']) == utilization_len
    assert payload_data['utilization']['hostname'] == HOST
    assert payload_data['utilization']['logical_processors'] == PROCESSOR_COUNT
    assert payload_data['utilization']['metadata_version'] == 3
    assert payload_data['utilization']['total_ram_mib'] == MEMORY
    assert payload_data['utilization']['boot_id'] == BOOT_ID
    vendors_len = any([with_aws, with_pcf, with_gcp, with_azure]) + with_docker
    if vendors_len:
        assert len(payload_data['utilization']['vendors']) == vendors_len

        # check ordering
        if with_aws:
            assert payload_data['utilization']['vendors']['aws'] == AWS
        elif with_pcf:
            assert payload_data['utilization']['vendors']['pcf'] == PCF
        elif with_gcp:
            assert payload_data['utilization']['vendors']['gcp'] == GCP
        elif with_azure:
            assert payload_data['utilization']['vendors']['azure'] == AZURE

        if with_docker:
            assert (payload_data['utilization']['vendors']['docker'] ==
                    DOCKER)
    else:
        assert 'vendors' not in payload_data['utilization']


@pytest.mark.parametrize('with_aws,with_pcf,with_gcp,with_azure,with_docker', [
    (True, False, False, False, True),
    (False, True, False, False, True),
    (False, False, True, False, True),
    (False, False, False, True, True),
    (True, False, False, False, False),
    (False, True, False, False, False),
    (False, False, True, False, False),
    (False, False, False, True, False),
    (True, True, True, True, True),
])
def test_create_connect_payload(with_aws, with_pcf, with_gcp, with_azure,
        with_docker):
    settings = default_settings()
    settings['utilization.detect_aws'] = with_aws
    settings['utilization.detect_pcf'] = with_pcf
    settings['utilization.detect_gcp'] = with_gcp
    settings['utilization.detect_azure'] = with_azure
    settings['utilization.detect_docker'] = with_docker
    payload = ApplicationSession._create_connect_payload(
            APP_NAME, LINKED_APPS, ENVIRONMENT, settings)
    payload_asserts(
            payload, with_aws=with_aws, with_pcf=with_pcf, with_gcp=with_gcp,
            with_azure=with_azure, with_docker=with_docker)


def test_create_connect_payload_no_vendors():
    settings = default_settings()
    settings['utilization.detect_aws'] = False
    settings['utilization.detect_pcf'] = False
    settings['utilization.detect_gcp'] = False
    settings['utilization.detect_azure'] = False
    settings['utilization.detect_docker'] = False
    payload = ApplicationSession._create_connect_payload(
            APP_NAME, LINKED_APPS, ENVIRONMENT, settings)
    payload_asserts(
            payload, with_aws=False, with_pcf=False, with_gcp=False,
            with_azure=False, with_docker=False)
