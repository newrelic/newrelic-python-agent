import os

from newrelic.common import system_info
from newrelic.core import data_collector as dc

from newrelic.core.data_collector import ApplicationSession

# Global constants used in tests
AGENT_VERSION = '2.0.0.0'
APP_NAME = 'test_app'
AWS = {'id': 'foo', 'type': 'bar', 'zone': 'baz'}
BROWSER_MONITORING_DEBUG = 'debug'
BROWSER_MONITORING_LOADER = 'loader'
CAPTURE_PARAMS = 'capture_params'
DISPLAY_NAME = 'display_name'
DOCKER_ID = '2a4f870e24a3b52eb9fe7f3e02858c31855e213e568cfa6c76cb046ffa5b8a28'
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

    def docker_container_id():
        return DOCKER_ID
    _backup_methods['docker_container_id'] = dc.docker_container_id
    dc.docker_container_id = docker_container_id

    def logical_processor_cnt():
        return PROCESSOR_COUNT
    _backup_methods['logical_proc_count'] = dc.logical_processor_count
    dc.logical_processor_count = logical_processor_cnt

    def total_physical_memory():
        return MEMORY
    _backup_methods['total_physical_memory'] = dc.total_physical_memory
    dc.total_physical_memory = total_physical_memory

    def aws_data():
        return AWS
    _backup_methods['aws_data'] = dc.aws_data
    dc.aws_data = aws_data

    _backup_methods['version'] = dc.version
    dc.version = AGENT_VERSION

def teardown_module(module):
    system_info.gethostname = _backup_methods['gethostname']
    os.getpid = _backup_methods['getpid']
    dc.docker_container_id = _backup_methods['docker_container_id']
    dc.logical_processor_count = _backup_methods['logical_proc_count']
    dc.total_physical_memory = _backup_methods['total_physical_memory']
    dc.aws_data = _backup_methods['aws_data']
    dc.version = _backup_methods['version']

def default_settings():
    return {'browser_monitoring.loader': BROWSER_MONITORING_LOADER,
            'browser_monitoring.debug': BROWSER_MONITORING_DEBUG,
            'capture_params': CAPTURE_PARAMS,
            'transaction_tracer.record_sql': RECORD_SQL,
            'high_security': HIGH_SECURITY,
            'labels': LABELS,
            'process_host.display_name': DISPLAY_NAME,
            'utilization.detect_aws': True,
            'utilization.detect_docker': True }

def payload_asserts(payload, with_aws=True, with_docker=True):
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
    assert payload_data['security_settings']['capture_params'] == CAPTURE_PARAMS
    assert payload_data['security_settings']['transaction_tracer'] == {
            'record_sql': RECORD_SQL}
    assert len(payload_data['settings']) == 2
    assert payload_data['settings']['browser_monitoring.loader'] == (
            BROWSER_MONITORING_LOADER)
    assert payload_data['settings']['browser_monitoring.debug'] == (
            BROWSER_MONITORING_DEBUG)
    utilization_len = 4 + (with_aws or with_docker)
    assert len(payload_data['utilization']) == utilization_len
    assert payload_data['utilization']['hostname'] == HOST
    assert payload_data['utilization']['logical_processors'] == PROCESSOR_COUNT
    assert payload_data['utilization']['metadata_version'] == 2
    assert payload_data['utilization']['total_ram_mib'] == MEMORY
    vendors_len = with_aws + with_docker
    if vendors_len:
        assert len(payload_data['utilization']['vendors']) == vendors_len
        if with_aws:
            assert payload_data['utilization']['vendors']['aws'] == AWS
        else:
            assert 'aws' not in payload_data['utilization']['vendors']
        if with_docker:
            assert payload_data['utilization']['vendors']['docker'] == {
                'id': DOCKER_ID}
        else:
            assert 'docker' not in payload_data['utilization']['vendors']
    else:
        assert 'vendors' not in payload_data['utilization']

def test_create_connect_payload():
    payload = ApplicationSession._create_connect_payload(
            APP_NAME, LINKED_APPS, ENVIRONMENT, default_settings())
    payload_asserts(payload)

def test_create_connect_payload_no_aws():
    settings = default_settings()
    settings['utilization.detect_aws'] = False
    payload = ApplicationSession._create_connect_payload(
            APP_NAME, LINKED_APPS, ENVIRONMENT, settings)
    payload_asserts(payload, with_aws=False)

def test_create_connect_payload_no_docker():
    settings = default_settings()
    settings['utilization.detect_docker'] = False
    payload = ApplicationSession._create_connect_payload(
            APP_NAME, LINKED_APPS, ENVIRONMENT, settings)
    payload_asserts(payload, with_docker=False)

def test_create_connect_payload_no_vendors():
    settings = default_settings()
    settings['utilization.detect_aws'] = False
    settings['utilization.detect_docker'] = False
    payload = ApplicationSession._create_connect_payload(
            APP_NAME, LINKED_APPS, ENVIRONMENT, settings)
    payload_asserts(payload, with_aws=False, with_docker=False)
