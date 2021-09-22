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

import collections
import pytest

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from newrelic.config import delete_setting, translate_deprecated_settings
from newrelic.common.object_names import callable_name
from newrelic.core.config import (global_settings_dump, flatten_settings,
    apply_config_setting, apply_server_side_settings, Settings,
    fetch_config_setting, global_settings)


def parameterize_local_config(settings_list):
    settings_object_list = []

    for settings in settings_list:
        settings_object = Settings()
        for name, value in settings.items():
            apply_config_setting(settings_object, name, value)
        settings_object_list.append(settings_object)

    return pytest.mark.parametrize('settings', settings_object_list)


_test_dictionary_local_config = [
    {
        'request_headers_map': {'NR-SESSION': 'BLANK'},
        'event_harvest_config': {
            'harvest_limits': {
                'analytic_event_data': 100,
                'custom_event_data': 100,
                'error_event_data': 8},
            'report_period_ms': 5000
        },
    }
]

_test_strip_proxy_details_local_configs = [
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': None,
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': None,
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'hostname',
        'proxy_port': 8888,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'hostname',
        'proxy_port': 8888,
        'proxy_user': 'username',
        'proxy_pass': 'password',

        'expected_proxy_host': 'hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'hostname',
        'proxy_port': 8888,
        'proxy_user': 'username',
        'proxy_pass': None,

        'expected_proxy_host': 'hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'hostname',
        'proxy_port': 8888,
        'proxy_user': 'username',
        'proxy_pass': '',

        'expected_proxy_host': 'hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'http://hostname',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'http://hostname:8888',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://hostname:8888',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'http://hostname',
        'proxy_port': None,
        'proxy_user': 'username',
        'proxy_pass': 'password',

        'expected_proxy_host': 'http://hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'http://hostname:8888',
        'proxy_port': None,
        'proxy_user': 'username',
        'proxy_pass': 'password',

        'expected_proxy_host': 'http://hostname:8888',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'http://username@hostname',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://****@hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'http://username@hostname:8888',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://****@hostname:8888',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'http://username:password@hostname',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://****:****@hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'http://username:password@hostname:8888',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://****:****@hostname:8888',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'https://username:password@hostname',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'https://****:****@hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',
        'encoding_key': 'ENCODING-KEY',
        'js_agent_loader': 'AGENT-LOADER-JS',
        'js_agent_file': 'AGENT-LOADER-FILE',

        'proxy_scheme': None,
        'proxy_host': 'https://username:password@hostname:8888',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'https://****:****@hostname:8888',
    },
]


@parameterize_local_config(_test_dictionary_local_config)
def test_dict_parse(settings):

    assert 'NR-SESSION' in settings.request_headers_map

    config = settings.event_harvest_config

    assert 'harvest_limits' in config
    assert 'report_period_ms' in config

    limits = config.harvest_limits

    assert 'analytic_event_data' in limits
    assert 'custom_event_data' in limits
    assert 'error_event_data' in limits


@parameterize_local_config(_test_strip_proxy_details_local_configs)
def test_strip_proxy_details(settings):
    assert 'license_key' in settings
    assert 'api_key' in settings

    assert 'proxy_scheme' in settings
    assert 'proxy_host' in settings
    assert 'proxy_port' in settings
    assert 'proxy_user' in settings
    assert 'proxy_port' in settings

    stripped = global_settings_dump(settings)

    # These should always be deleted.

    assert 'license_key' not in stripped
    assert 'api_key' not in stripped

    # These should be obfuscated or None.

    obfuscated = '****'

    assert stripped['proxy_user'] in (None, obfuscated)
    assert stripped['proxy_pass'] in (None, obfuscated)

    # The proxy_host and proxy_port will be preserved but proxy_host
    # needs to be checked to make sure it doesn't contain a username and
    # password. Do this through parsing to make sure not breaking the
    # structure in some way and also direct comparison of what is
    # expected as backup.

    assert 'proxy_scheme' in settings
    assert 'proxy_host' in stripped
    assert 'proxy_port' in stripped

    proxy_host = stripped['proxy_host']
    expected_proxy_host = stripped['expected_proxy_host']

    if proxy_host is not None:
        components = urlparse.urlparse(proxy_host)

        if components.username:
            assert components.username == obfuscated
        if components.password:
            assert components.password == obfuscated

    assert proxy_host == expected_proxy_host


def test_delete_setting():
    d = {'transaction_tracer.capture_attributes': True}
    settings = apply_server_side_settings(d)
    assert 'capture_attributes' in settings.transaction_tracer

    delete_setting(settings, 'transaction_tracer.capture_attributes')
    assert 'capture_attributes' not in settings.transaction_tracer


def test_delete_setting_absent():
    settings = apply_server_side_settings()
    assert 'capture_attributes' not in settings.transaction_tracer

    delete_setting(settings, 'transaction_tracer.capture_attributes')
    assert 'capture_attributes' not in settings.transaction_tracer


def test_delete_setting_parent():
    settings = apply_server_side_settings()
    assert 'transaction_tracer' in settings
    assert 'attributes' in settings.transaction_tracer

    delete_setting(settings, 'transaction_tracer')
    assert 'transaction_tracer' not in settings


# Build a series of tests for `translate_deprecated_setting`.
#
# Each test will consist of an old setting and new setting.
# For each setting, there are 2 variations:
#
#       'value' == 'default'
#       'value' != 'default'
TSetting = collections.namedtuple('TSetting', ['name', 'value', 'default'])

translate_settings_tests = [
    (
        TSetting('transaction_tracer.capture_attributes', True, True),
        TSetting('transaction_tracer.attributes.enabled', False, True)
    ),
    (
        TSetting('transaction_tracer.capture_attributes', False, True),
        TSetting('transaction_tracer.attributes.enabled', True, True)
    ),
    (
        TSetting('error_collector.capture_attributes', True, True),
        TSetting('error_collector.attributes.enabled', False, True)
    ),
    (
        TSetting('error_collector.capture_attributes', False, True),
        TSetting('error_collector.attributes.enabled', True, True)
    ),
    (
        TSetting('browser_monitoring.capture_attributes', False, False),
        TSetting('browser_monitoring.attributes.enabled', True, False)
    ),
    (
        TSetting('browser_monitoring.capture_attributes', True, False),
        TSetting('browser_monitoring.attributes.enabled', False, False)
    ),
    (
        TSetting('analytics_events.capture_attributes', True, True),
        TSetting('transaction_events.attributes.enabled', False, True)
    ),
    (
        TSetting('analytics_events.capture_attributes', False, True),
        TSetting('transaction_events.attributes.enabled', True, True)
    ),
    (
        TSetting('analytics_events.enabled', True, True),
        TSetting('transaction_events.enabled', False, True)
    ),
    (
        TSetting('analytics_events.enabled', False, True),
        TSetting('transaction_events.enabled', True, True)
    ),
    (
        TSetting('analytics_events.max_samples_stored', 1200, 1200),
        TSetting('event_harvest_config.harvest_limits.analytic_event_data',
            9999, 1200)
    ),
    (
        TSetting('analytics_events.max_samples_stored', 9999, 1200),
        TSetting('event_harvest_config.harvest_limits.analytic_event_data',
            1200, 1200)
    ),
    (
        TSetting('transaction_events.max_samples_stored', 1200, 1200),
        TSetting('event_harvest_config.harvest_limits.analytic_event_data',
            9999, 1200)
    ),
    (
        TSetting('transaction_events.max_samples_stored', 9999, 1200),
        TSetting('event_harvest_config.harvest_limits.analytic_event_data',
            1200, 1200)
    ),
    (
        TSetting('span_events.max_samples_stored', 1000, 2000),
        TSetting('event_harvest_config.harvest_limits.span_event_data',
            9999, 2000)
    ),
    (
        TSetting('span_events.max_samples_stored', 9999, 2000),
        TSetting('event_harvest_config.harvest_limits.span_event_data',
            1000, 2000)
    ),
    (
        TSetting('error_collector.max_event_samples_stored', 100, 100),
        TSetting('event_harvest_config.harvest_limits.error_event_data',
            9999, 100)
    ),
    (
        TSetting('error_collector.max_event_samples_stored', 9999, 100),
        TSetting('event_harvest_config.harvest_limits.error_event_data',
            100, 100)
    ),
    (
        TSetting('custom_insights_events.max_samples_stored', 1200, 1200),
        TSetting('event_harvest_config.harvest_limits.custom_event_data',
            9999, 1200)
    ),
    (
        TSetting('custom_insights_events.max_samples_stored', 9999, 1200),
        TSetting('event_harvest_config.harvest_limits.custom_event_data',
            1200, 1200)
    ),
(
        TSetting('error_collector.ignore_errors', callable_name(ValueError), []),
        TSetting('error_collector.ignore_classes', callable_name(ValueError), [])
    ),

]


@pytest.mark.parametrize('old,new', translate_settings_tests)
def test_translate_deprecated_setting_without_new_setting(old, new):
    # Before: deprecated setting will be in settings object.
    #         new setting will be in settings object and have default value
    #
    # After:  deprecated setting will *NOT* be in settings object
    #         new setting will have value of deprecated setting

    settings = apply_server_side_settings()
    apply_config_setting(settings, old.name, old.value)

    assert fetch_config_setting(settings, old.name) == old.value
    assert fetch_config_setting(settings, new.name) == new.default

    cached = [(old.name, old.value)]
    result = translate_deprecated_settings(settings, cached)

    assert result is settings
    assert old.name not in flatten_settings(result)
    assert fetch_config_setting(result, new.name) == old.value


@pytest.mark.parametrize('old,new', translate_settings_tests)
def test_translate_deprecated_setting_with_new_setting(old, new):
    # Before: deprecated setting will be in settings object.
    #         new setting will be in settings object and have its value
    #
    # After:  deprecated setting will *NOT* be in settings object
    #         new setting will still have its value (remain unchanged)

    settings = apply_server_side_settings()
    apply_config_setting(settings, old.name, old.value)
    apply_config_setting(settings, new.name, new.value)

    assert fetch_config_setting(settings, old.name) == old.value
    assert fetch_config_setting(settings, new.name) == new.value

    cached = [(old.name, old.value), (new.name, new.value)]
    result = translate_deprecated_settings(settings, cached)

    assert result is settings
    assert old.name not in flatten_settings(result)
    assert fetch_config_setting(result, new.name) == new.value


@pytest.mark.parametrize('old,new', translate_settings_tests)
def test_translate_deprecated_setting_without_old_setting(old, new):
    # Before: deprecated setting will *NOT* be in settings object.
    #         new setting will be in settings object and have its value
    #
    # After:  deprecated setting will still *NOT* be in settings object
    #         new setting will still have its value (remain unchanged)

    settings = apply_server_side_settings()
    apply_config_setting(settings, new.name, new.value)

    assert old.name not in flatten_settings(settings)
    assert fetch_config_setting(settings, new.name) == new.value

    cached = [(new.name, new.value)]
    result = translate_deprecated_settings(settings, cached)

    assert result is settings
    assert old.name not in flatten_settings(result)
    assert fetch_config_setting(result, new.name) == new.value


def test_translate_deprecated_ignored_params_without_new_setting():
    ignored_params = ['foo', 'bar']
    settings = apply_server_side_settings()
    apply_config_setting(settings, 'ignored_params', ignored_params)

    assert 'foo' in settings.ignored_params
    assert 'bar' in settings.ignored_params
    assert len(settings.attributes.exclude) == 0

    cached = [('ignored_params', ignored_params)]
    result = translate_deprecated_settings(settings, cached)

    assert result is settings
    assert 'request.parameters.foo' in result.attributes.exclude
    assert 'request.parameters.bar' in result.attributes.exclude
    assert 'ignored_params' not in result


def test_translate_deprecated_ignored_params_with_new_setting():
    ignored_params = ['foo', 'bar']
    attr_exclude = ['request.parameters.foo']
    settings = apply_server_side_settings()
    apply_config_setting(settings, 'ignored_params', ignored_params)
    apply_config_setting(settings, 'attributes.exclude', attr_exclude)

    assert 'foo' in settings.ignored_params
    assert 'bar' in settings.ignored_params
    assert 'request.parameters.foo' in settings.attributes.exclude

    cached = [
        ('ignored_params', ignored_params),
        ('attributes.exclude', attr_exclude)
    ]
    result = translate_deprecated_settings(settings, cached)

    # ignored_params are not merged!

    assert result is settings
    assert 'request.parameters.foo' in result.attributes.exclude
    assert 'request.parameters.bar' not in result.attributes.exclude
    assert 'ignored_params' not in result


@pytest.mark.parametrize('name,expected_value', (
    ('agent_run_id', None),
    ('entity_guid', None),
    ('distributed_tracing.exclude_newrelic_header', False),
))
def test_default_values(name, expected_value):
    settings = global_settings()
    value = fetch_config_setting(settings, name)
    assert value == expected_value
