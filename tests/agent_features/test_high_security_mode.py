import os
import pytest
import webtest

from testing_support.fixtures import (override_application_settings,
    validate_custom_parameters, validate_transaction_errors,
    validate_request_params)

from newrelic.agent import (background_task, add_custom_parameter,
    record_exception, wsgi_application)

from newrelic.core.config import (global_settings, Settings,
    apply_config_setting)

from newrelic.config import apply_local_high_security_mode_setting
from newrelic.core.data_collector import apply_high_security_mode_fixups

def test_hsm_configuration_default():
    # Global default should always be off.

    settings = global_settings()
    assert 'NEW_RELIC_HIGH_SECURITY_MODE' not in os.environ
    assert settings.high_security is False

_hsm_local_config_file_settings_disabled = [
    {
        'high_security': False,
        'ssl': True,
        'capture_params': True,
        'transaction_tracer.record_sql': 'raw',
    },
    {
        'high_security': False,
        'ssl': False,
        'capture_params': False,
        'transaction_tracer.record_sql': 'raw',
    },
    {
        'high_security': False,
        'ssl': False,
        'capture_params': False,
        'transaction_tracer.record_sql': 'obfuscated',
    },
    {
        'high_security': False,
        'ssl': False,
        'capture_params': False,
        'transaction_tracer.record_sql': 'off',
    },
]

_hsm_local_config_file_settings_enabled = [
    {
        'high_security': True,
        'ssl': True,
        'capture_params': True,
        'transaction_tracer.record_sql': 'raw',
    },
    {
        'high_security': True,
        'ssl': False,
        'capture_params': True,
        'transaction_tracer.record_sql': 'raw',
    },
    {
        'high_security': True,
        'ssl': True,
        'capture_params': False,
        'transaction_tracer.record_sql': 'raw',
    },
    {
        'high_security': True,
        'ssl': True,
        'capture_params': True,
        'transaction_tracer.record_sql': 'obfuscated',
    },
    {
        'high_security': True,
        'ssl': True,
        'capture_params': True,
        'transaction_tracer.record_sql': 'off',
    },
]

def parameterize_hsm_local_config(settings_list):
    settings_object_list = []

    for settings in settings_list:
        settings_object = Settings()
        for name, value in settings.items():
            apply_config_setting(settings_object, name, value)
        settings_object_list.append(settings_object)

    return pytest.mark.parametrize('settings', settings_object_list)

@parameterize_hsm_local_config(_hsm_local_config_file_settings_disabled)
def test_local_config_file_hsm_override_disabled(settings):
    original_ssl = settings.ssl
    original_capture_params = settings.capture_params
    original_record_sql = settings.transaction_tracer.record_sql

    apply_local_high_security_mode_setting(settings)

    assert settings.ssl == original_ssl
    assert settings.capture_params == original_capture_params
    assert settings.transaction_tracer.record_sql == original_record_sql

@parameterize_hsm_local_config(_hsm_local_config_file_settings_enabled)
def test_local_config_file_hsm_override_enabled(settings):
    apply_local_high_security_mode_setting(settings)

    assert settings.ssl
    assert not settings.capture_params
    assert settings.transaction_tracer.record_sql in ('off', 'obfuscated')

_hsm_server_side_config_settings_disabled = [
    (
        {
            'high_security': False,
            'capture_params': False,
            'transaction_tracer.record_sql': 'obfuscated',
        },
        {
            u'agent_config': {
                u'capture_params': True,
                u'transaction_tracer.record_sql': u'raw',
            },
        },
    ),
    (
        {
            'high_security': False,
            'capture_params': True,
            'transaction_tracer.record_sql': 'raw',
        },
        {
            u'agent_config': {
                u'capture_params': False,
                'transaction_tracer.record_sql': u'off',
            },
        },
    ),
]

_hsm_server_side_config_settings_enabled = [
    (
        {
            'high_security': True,
            'capture_params': False,
            'transaction_tracer.record_sql': 'obfuscated',
        },
        {
            u'high_security': True,
            u'capture_params': False,
            u'transaction_tracer.record_sql': u'obfuscated',
            u'agent_config': {
                u'capture_params': False,
                u'transaction_tracer.record_sql': u'obfuscated',
            },
        },
    ),
    (
        {
            'high_security': True,
            'capture_params': False,
            'transaction_tracer.record_sql': 'obfuscated',
        },
        {
            u'high_security': True,
            u'capture_params': False,
            u'transaction_tracer.record_sql': u'obfuscated',
            u'agent_config': {
                u'capture_params': True,
                u'transaction_tracer.record_sql': u'raw',
            },
        },
    ),
]

@pytest.mark.parametrize('local_settings,server_settings',
        _hsm_server_side_config_settings_disabled)
def test_remote_config_hsm_fixups_disabled(local_settings, server_settings):
    assert 'high_security' in local_settings
    assert local_settings['high_security'] == False

    assert u'high_security' not in server_settings

    agent_config = server_settings['agent_config']

    original_capture_params = agent_config['capture_params']
    original_record_sql = agent_config['transaction_tracer.record_sql']

    settings = apply_high_security_mode_fixups(local_settings, server_settings)

    agent_config = server_settings['agent_config']

    assert u'high_security' not in settings

    assert agent_config['capture_params'] == original_capture_params
    assert agent_config['transaction_tracer.record_sql'] == original_record_sql

@pytest.mark.parametrize('local_settings,server_settings',
        _hsm_server_side_config_settings_enabled)
def test_remote_config_hsm_fixups_enabled(local_settings, server_settings):
    assert 'high_security' in local_settings
    assert local_settings['high_security'] == True

    assert u'high_security' in server_settings

    settings = apply_high_security_mode_fixups(local_settings, server_settings)

    agent_config = server_settings['agent_config']

    assert u'high_security' not in settings
    assert u'capture_params' not in settings
    assert u'transaction_tracer.record_sql' not in settings

    assert u'capture_params' not in agent_config
    assert u'transaction_tracer.record_sql' not in agent_config

def test_remote_config_hsm_fixups_server_side_disabled():
    local_settings = {'high_security': True}
    server_settings = {'high_security': True}

    settings = apply_high_security_mode_fixups(local_settings, server_settings)

    assert 'high_security' not in settings

_test_transaction_settings_hsm_disabled = {
    'high_security': False }

_test_transaction_settings_hsm_enabled = {
    'high_security': True }

@override_application_settings(_test_transaction_settings_hsm_disabled)
@validate_custom_parameters(required_params=[('key', 'value')])
@background_task()
def test_other_transaction_hsm_custom_parameters_disabled():
    add_custom_parameter('key', 'value')

@override_application_settings(_test_transaction_settings_hsm_enabled)
@validate_custom_parameters(forgone_params=[('key', 'value')])
@background_task()
def test_other_transaction_hsm_custom_parameters_enabled():
    add_custom_parameter('key', 'value')

class TestException(Exception): pass

_test_exception_name = '%s:%s' % (__name__, TestException.__name__)

@override_application_settings(_test_transaction_settings_hsm_disabled)
@validate_transaction_errors(errors=[_test_exception_name],
    required_params=[('key-1', 'value-1'), ('key-2', 'value-2')])
@background_task()
def test_other_transaction_hsm_error_parameters_disabled():
    add_custom_parameter('key-1', 'value-1')
    try:
        raise TestException()
    except Exception:
        record_exception(params={'key-2': 'value-2'})

@override_application_settings(_test_transaction_settings_hsm_enabled)
@validate_transaction_errors(errors=[_test_exception_name],
    forgone_params=[('key-1', 'value-1'), ('key-2', 'value-2')])
@background_task()
def test_other_transaction_hsm_error_parameters_enabled():
    add_custom_parameter('key-1', 'value-1')
    try:
        raise TestException()
    except Exception:
        record_exception(params={'key-2': 'value-2'})

@wsgi_application()
def target_wsgi_application_capture_params(environ, start_response):
    status = '200 OK'
    output = b'Hello World!'

    response_headers = [('Content-Type', 'text/plain; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

_test_transaction_settings_hsm_enabled_capture_params = {
    'high_security': True,
    'capture_params': False }

@override_application_settings(
    _test_transaction_settings_hsm_enabled_capture_params)
@validate_request_params(forgone_params=[('key-1', 'value-1')])
def test_other_transaction_hsm_environ_capture_request_params_disabled():
    target_application = webtest.TestApp(
            target_wsgi_application_capture_params)

    environ = {}
    environ['newrelic.capture_request_params'] = False

    response = target_application.get('/', params='key-1=value-1',
            extra_environ=environ)

@override_application_settings(
    _test_transaction_settings_hsm_enabled_capture_params)
@validate_request_params(forgone_params=[('key-1', 'value-1')])
def test_other_transaction_hsm_environ_capture_request_params_enabled():
    target_application = webtest.TestApp(
            target_wsgi_application_capture_params)

    environ = {}
    environ['newrelic.capture_request_params'] = True

    response = target_application.get('/', params='key-1=value-1',
            extra_environ=environ)
