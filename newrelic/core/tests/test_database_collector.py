import os
import socket
import newrelic.core.data_collector

from newrelic.core.data_collector import ApplicationSession

# Global constants used in tests
AGENT_VERSION = '2.0.0.0'
APP_NAME = 'test_app'
AWS = {'aws': {'id': 'foo', 'type': 'bar', 'zone': 'baz'}}
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
LOCAL_CONFIG_APP_NAME = [APP_NAME] + LINKED_APPS
LOCAL_CONFIG_ID = ','.join(LOCAL_CONFIG_APP_NAME)
PID = 123
PROCESSOR_COUNT = 4
RECORD_SQL = 'record_sql'

# Mock out the calls used to create the connect local_config.
def setup_module(module):
    def gethostname():
        return HOST
    socket.gethostname = gethostname

    def getpid():
        return PID
    os.getpid = getpid

    def docker_container_id():
        return DOCKER_ID
    newrelic.core.data_collector.docker_container_id = docker_container_id

    def logical_processor_cnt():
        return PROCESSOR_COUNT
    newrelic.core.data_collector.logical_processor_count = logical_processor_cnt

    def total_physical_memory():
        return MEMORY
    newrelic.core.data_collector.total_physical_memory = total_physical_memory

    def aws_data():
        return AWS
    newrelic.core.data_collector.aws_data = aws_data

    newrelic.core.data_collector.version = AGENT_VERSION

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

def local_config_asserts(local_config, with_aws=True, with_docker=True):
    assert local_config['agent_version'] == AGENT_VERSION
    assert local_config['app_name'] == LOCAL_CONFIG_APP_NAME
    assert local_config['display_host'] == DISPLAY_NAME
    assert local_config['environment'] == ENVIRONMENT
    assert local_config['high_security'] == HIGH_SECURITY
    assert local_config['host'] == HOST
    assert local_config['identifier'] == LOCAL_CONFIG_ID
    assert local_config['labels'] == LABELS
    assert local_config['language'] == 'python'
    assert local_config['pid'] == PID
    assert len(local_config['security_settings']) == 2
    assert local_config['security_settings']['capture_params'] == CAPTURE_PARAMS
    assert local_config['security_settings']['transaction_tracer'] == {
            'record_sql': RECORD_SQL}
    assert len(local_config['settings']) == 2
    assert local_config['settings']['browser_monitoring.loader'] == (
            BROWSER_MONITORING_LOADER)
    assert local_config['settings']['browser_monitoring.debug'] == (
            BROWSER_MONITORING_DEBUG)
    utilization_len = 4 + (with_aws or with_docker)
    assert len(local_config['utilization']) == utilization_len
    assert local_config['utilization']['hostname'] == HOST
    assert local_config['utilization']['logical_processors'] == PROCESSOR_COUNT
    assert local_config['utilization']['metadata_version'] == 1
    assert local_config['utilization']['total_ram_mib'] == MEMORY
    vendors_len = with_aws + with_docker
    if vendors_len:
        assert len(local_config['utilization']['vendors']) == vendors_len
        if with_aws:
            assert local_config['utilization']['vendors']['aws'] == AWS['aws']
        if with_docker:
            assert local_config['utilization']['vendors']['docker'] == {
                'id': DOCKER_ID}

def test_create_connect_local_config():
    local_config = ApplicationSession._create_connect_local_config(
            APP_NAME, LINKED_APPS, ENVIRONMENT, default_settings())
    local_config_asserts(local_config)

def test_create_connect_local_config_no_aws():
    settings = default_settings()
    settings['utilization.detect_aws'] = False
    local_config = ApplicationSession._create_connect_local_config(
            APP_NAME, LINKED_APPS, ENVIRONMENT, settings)
    local_config_asserts(local_config, with_aws=False)

def test_create_connect_local_config_no_docker():
    settings = default_settings()
    settings['utilization.detect_docker'] = False
    local_config = ApplicationSession._create_connect_local_config(
            APP_NAME, LINKED_APPS, ENVIRONMENT, settings)
    local_config_asserts(local_config, with_docker=False)

def test_create_connect_local_config_no_vendors():
    settings = default_settings()
    settings['utilization.detect_aws'] = False
    settings['utilization.detect_docker'] = False
    local_config = ApplicationSession._create_connect_local_config(
            APP_NAME, LINKED_APPS, ENVIRONMENT, settings)
    local_config_asserts(local_config, with_aws=False, with_docker=False)
