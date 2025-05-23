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
import copy
import logging
import pathlib
import sys
import tempfile
import urllib.parse as urlparse

import pytest
from testing_support.fixtures import override_generic_settings

from newrelic.api.exceptions import ConfigurationError
from newrelic.common.object_names import callable_name
from newrelic.config import (
    _reset_config_parser,
    _reset_configuration_done,
    _reset_instrumentation_done,
    delete_setting,
    initialize,
    translate_deprecated_settings,
)
from newrelic.core.config import (
    Settings,
    _map_aws_account_id,
    apply_config_setting,
    apply_server_side_settings,
    fetch_config_setting,
    flatten_settings,
    global_settings,
    global_settings_dump,
)

SKIP_IF_NOT_PY311 = pytest.mark.skipif(sys.version_info < (3, 11), reason="TOML not in the standard library.")


@pytest.fixture
def collector_available_fixture():
    # Disable fixture that requires real application to exist for this file
    pass


@pytest.fixture(scope="module", autouse=True)
def restore_settings_fixture():
    # Backup settings from before this test file runs
    original_settings = global_settings()
    backup = copy.deepcopy(original_settings.__dict__)

    # Run tests
    yield

    # Restore settings after tests run
    original_settings.__dict__.clear()
    original_settings.__dict__.update(backup)


def function_to_trace():
    pass


def parameterize_local_config(settings_list):
    settings_object_list = []

    for settings in settings_list:
        settings_object = Settings()
        for name, value in settings.items():
            apply_config_setting(settings_object, name, value)
        settings_object_list.append(settings_object)

    return pytest.mark.parametrize("settings", settings_object_list)


_test_dictionary_local_config = [
    {
        "request_headers_map": {"NR-SESSION": "BLANK"},
        "event_harvest_config": {
            "harvest_limits": {
                "analytic_event_data": 100,
                "custom_event_data": 100,
                "error_event_data": 8,
                "log_event_data": 100,
            },
            "report_period_ms": 5000,
        },
    }
]

_test_strip_proxy_details_local_configs = [
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": None,
        "proxy_port": None,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": None,
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "hostname",
        "proxy_port": 8888,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": "hostname",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "hostname",
        "proxy_port": 8888,
        "proxy_user": "username",
        "proxy_pass": "password",
        "expected_proxy_host": "hostname",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "hostname",
        "proxy_port": 8888,
        "proxy_user": "username",
        "proxy_pass": None,
        "expected_proxy_host": "hostname",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "hostname",
        "proxy_port": 8888,
        "proxy_user": "username",
        "proxy_pass": "",
        "expected_proxy_host": "hostname",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "http://hostname",
        "proxy_port": None,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": "http://hostname",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "http://hostname:8888",
        "proxy_port": None,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": "http://hostname:8888",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "http://hostname",
        "proxy_port": None,
        "proxy_user": "username",
        "proxy_pass": "password",
        "expected_proxy_host": "http://hostname",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "http://hostname:8888",
        "proxy_port": None,
        "proxy_user": "username",
        "proxy_pass": "password",
        "expected_proxy_host": "http://hostname:8888",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "http://username@hostname",
        "proxy_port": None,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": "http://****@hostname",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "http://username@hostname:8888",
        "proxy_port": None,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": "http://****@hostname:8888",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "http://username:password@hostname",
        "proxy_port": None,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": "http://****:****@hostname",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "http://username:password@hostname:8888",
        "proxy_port": None,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": "http://****:****@hostname:8888",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "https://username:password@hostname",
        "proxy_port": None,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": "https://****:****@hostname",
    },
    {
        "license_key": "LICENSE-KEY",
        "api_key": "API-KEY",
        "encoding_key": "ENCODING-KEY",
        "js_agent_loader": "AGENT-LOADER-JS",
        "js_agent_file": "AGENT-LOADER-FILE",
        "proxy_scheme": None,
        "proxy_host": "https://username:password@hostname:8888",
        "proxy_port": None,
        "proxy_user": None,
        "proxy_pass": None,
        "expected_proxy_host": "https://****:****@hostname:8888",
    },
]


@parameterize_local_config(_test_dictionary_local_config)
def test_dict_parse(settings):
    assert "NR-SESSION" in settings.request_headers_map

    config = settings.event_harvest_config

    assert "harvest_limits" in config
    assert "report_period_ms" in config

    limits = config.harvest_limits

    assert "analytic_event_data" in limits
    assert "custom_event_data" in limits
    assert "error_event_data" in limits
    assert "log_event_data" in limits


@parameterize_local_config(_test_strip_proxy_details_local_configs)
def test_strip_proxy_details(settings):
    assert "license_key" in settings
    assert "api_key" in settings

    assert "proxy_scheme" in settings
    assert "proxy_host" in settings
    assert "proxy_port" in settings
    assert "proxy_user" in settings
    assert "proxy_port" in settings

    stripped = global_settings_dump(settings)

    # These should always be deleted.

    assert "license_key" not in stripped
    assert "api_key" not in stripped

    # These should be obfuscated or None.

    obfuscated = "****"

    assert stripped["proxy_user"] in (None, obfuscated)
    assert stripped["proxy_pass"] in (None, obfuscated)

    # The proxy_host and proxy_port will be preserved but proxy_host
    # needs to be checked to make sure it doesn't contain a username and
    # password. Do this through parsing to make sure not breaking the
    # structure in some way and also direct comparison of what is
    # expected as backup.

    assert "proxy_scheme" in settings
    assert "proxy_host" in stripped
    assert "proxy_port" in stripped

    proxy_host = stripped["proxy_host"]
    expected_proxy_host = stripped["expected_proxy_host"]

    if proxy_host is not None:
        components = urlparse.urlparse(proxy_host)

        if components.username:
            assert components.username == obfuscated
        if components.password:
            assert components.password == obfuscated

    assert proxy_host == expected_proxy_host


def test_delete_setting():
    d = {"transaction_tracer.capture_attributes": True}
    settings = apply_server_side_settings(d)
    assert "capture_attributes" in settings.transaction_tracer

    delete_setting(settings, "transaction_tracer.capture_attributes")
    assert "capture_attributes" not in settings.transaction_tracer


def test_delete_setting_absent():
    settings = apply_server_side_settings()
    assert "capture_attributes" not in settings.transaction_tracer

    delete_setting(settings, "transaction_tracer.capture_attributes")
    assert "capture_attributes" not in settings.transaction_tracer


def test_delete_setting_parent():
    settings = apply_server_side_settings()
    assert "transaction_tracer" in settings
    assert "attributes" in settings.transaction_tracer

    delete_setting(settings, "transaction_tracer")
    assert "transaction_tracer" not in settings


# Build a series of tests for `translate_deprecated_setting`.
#
# Each test will consist of an old setting and new setting.
# For each setting, there are 2 variations:
#
#       'value' == 'default'
#       'value' != 'default'
TSetting = collections.namedtuple("TSetting", ["name", "value", "default"])

translate_settings_tests = [
    (
        TSetting("strip_exception_messages.whitelist", [], []),
        TSetting("strip_exception_messages.allowlist", ["non-default-value"], []),
    ),
    (
        TSetting("strip_exception_messages.whitelist", ["non-default-value"], []),
        TSetting("strip_exception_messages.allowlist", [], []),
    ),
    (
        TSetting("transaction_tracer.capture_attributes", True, True),
        TSetting("transaction_tracer.attributes.enabled", False, True),
    ),
    (
        TSetting("transaction_tracer.capture_attributes", False, True),
        TSetting("transaction_tracer.attributes.enabled", True, True),
    ),
    (
        TSetting("error_collector.capture_attributes", True, True),
        TSetting("error_collector.attributes.enabled", False, True),
    ),
    (
        TSetting("error_collector.capture_attributes", False, True),
        TSetting("error_collector.attributes.enabled", True, True),
    ),
    (
        TSetting("browser_monitoring.capture_attributes", False, False),
        TSetting("browser_monitoring.attributes.enabled", True, False),
    ),
    (
        TSetting("browser_monitoring.capture_attributes", True, False),
        TSetting("browser_monitoring.attributes.enabled", False, False),
    ),
    (
        TSetting("analytics_events.capture_attributes", True, True),
        TSetting("transaction_events.attributes.enabled", False, True),
    ),
    (
        TSetting("analytics_events.capture_attributes", False, True),
        TSetting("transaction_events.attributes.enabled", True, True),
    ),
    (TSetting("analytics_events.enabled", True, True), TSetting("transaction_events.enabled", False, True)),
    (TSetting("analytics_events.enabled", False, True), TSetting("transaction_events.enabled", True, True)),
    (
        TSetting("analytics_events.max_samples_stored", 1200, 1200),
        TSetting("event_harvest_config.harvest_limits.analytic_event_data", 9999, 1200),
    ),
    (
        TSetting("analytics_events.max_samples_stored", 9999, 1200),
        TSetting("event_harvest_config.harvest_limits.analytic_event_data", 1200, 1200),
    ),
    (
        TSetting("transaction_events.max_samples_stored", 1200, 1200),
        TSetting("event_harvest_config.harvest_limits.analytic_event_data", 9999, 1200),
    ),
    (
        TSetting("transaction_events.max_samples_stored", 9999, 1200),
        TSetting("event_harvest_config.harvest_limits.analytic_event_data", 1200, 1200),
    ),
    (
        TSetting("span_events.max_samples_stored", 1000, 2000),
        TSetting("event_harvest_config.harvest_limits.span_event_data", 9999, 2000),
    ),
    (
        TSetting("span_events.max_samples_stored", 9999, 2000),
        TSetting("event_harvest_config.harvest_limits.span_event_data", 1000, 2000),
    ),
    (
        TSetting("error_collector.max_event_samples_stored", 100, 100),
        TSetting("event_harvest_config.harvest_limits.error_event_data", 9999, 100),
    ),
    (
        TSetting("error_collector.max_event_samples_stored", 9999, 100),
        TSetting("event_harvest_config.harvest_limits.error_event_data", 100, 100),
    ),
    (
        TSetting("custom_insights_events.max_samples_stored", 3600, 3600),
        TSetting("event_harvest_config.harvest_limits.custom_event_data", 9999, 3600),
    ),
    (
        TSetting("custom_insights_events.max_samples_stored", 9999, 3600),
        TSetting("event_harvest_config.harvest_limits.custom_event_data", 3600, 3600),
    ),
    (
        TSetting("application_logging.forwarding.max_samples_stored", 10000, 10000),
        TSetting("event_harvest_config.harvest_limits.log_event_data", 99999, 10000),
    ),
    (
        TSetting("application_logging.forwarding.max_samples_stored", 99999, 10000),
        TSetting("event_harvest_config.harvest_limits.log_event_data", 10000, 10000),
    ),
    (
        TSetting("error_collector.ignore_errors", [], []),
        TSetting("error_collector.ignore_classes", callable_name(ValueError), []),
    ),
    (
        TSetting("error_collector.ignore_errors", callable_name(ValueError), []),
        TSetting("error_collector.ignore_classes", [], []),
    ),
]


@pytest.mark.parametrize("old,new", translate_settings_tests)
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


@pytest.mark.parametrize("old,new", translate_settings_tests)
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


@pytest.mark.parametrize("old,new", translate_settings_tests)
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
    ignored_params = ["foo", "bar"]
    settings = apply_server_side_settings()
    apply_config_setting(settings, "ignored_params", ignored_params)

    assert "foo" in settings.ignored_params
    assert "bar" in settings.ignored_params
    assert len(settings.attributes.exclude) == 0

    cached = [("ignored_params", ignored_params)]
    result = translate_deprecated_settings(settings, cached)

    assert result is settings
    assert "request.parameters.foo" in result.attributes.exclude
    assert "request.parameters.bar" in result.attributes.exclude
    assert "ignored_params" not in result


def test_translate_deprecated_ignored_params_with_new_setting():
    ignored_params = ["foo", "bar"]
    attr_exclude = ["request.parameters.foo"]
    settings = apply_server_side_settings()
    apply_config_setting(settings, "ignored_params", ignored_params)
    apply_config_setting(settings, "attributes.exclude", attr_exclude)

    assert "foo" in settings.ignored_params
    assert "bar" in settings.ignored_params
    assert "request.parameters.foo" in settings.attributes.exclude

    cached = [("ignored_params", ignored_params), ("attributes.exclude", attr_exclude)]
    result = translate_deprecated_settings(settings, cached)

    # ignored_params are not merged!

    assert result is settings
    assert "request.parameters.foo" in result.attributes.exclude
    assert "request.parameters.bar" not in result.attributes.exclude
    assert "ignored_params" not in result


@pytest.mark.parametrize(
    "name,expected_value",
    (
        ("agent_run_id", None),
        ("entity_guid", None),
        ("distributed_tracing.exclude_newrelic_header", False),
        ("otlp_host", "otlp.nr-data.net"),
        ("otlp_port", 0),
    ),
)
@override_generic_settings(global_settings(), {"host": "collector.newrelic.com"})
def test_default_values(name, expected_value):
    settings = global_settings()
    value = fetch_config_setting(settings, name)
    assert value == expected_value


def test_initialize():
    initialize()


newrelic_ini_contents = b"""
[newrelic]
app_name = Python Agent Test (agent_features)
"""


def test_initialize_raises_if_config_does_not_match_previous():
    error_message = "Configuration has already been done against differing configuration file or environment.*"
    with pytest.raises(ConfigurationError, match=error_message):
        with tempfile.NamedTemporaryFile() as f:
            f.write(newrelic_ini_contents)
            f.seek(0)

            initialize(config_file=f.name)


def test_initialize_via_config_file():
    _reset_configuration_done()
    with tempfile.NamedTemporaryFile() as f:
        f.write(newrelic_ini_contents)
        f.seek(0)

        initialize(config_file=f.name)


def test_initialize_no_config_file():
    _reset_configuration_done()
    initialize()


def test_initialize_config_file_does_not_exist():
    _reset_configuration_done()
    error_message = "Unable to open configuration file does-not-exist."
    with pytest.raises(ConfigurationError, match=error_message):
        initialize(config_file="does-not-exist")


def test_initialize_environment():
    _reset_configuration_done()
    with tempfile.NamedTemporaryFile() as f:
        f.write(newrelic_ini_contents)
        f.seek(0)

        initialize(config_file=f.name, environment="developement")


def test_initialize_log_level():
    _reset_configuration_done()
    with tempfile.NamedTemporaryFile() as f:
        f.write(newrelic_ini_contents)
        f.seek(0)

        initialize(config_file=f.name, log_level="debug")


def test_initialize_log_file():
    _reset_configuration_done()
    with tempfile.NamedTemporaryFile() as f:
        f.write(newrelic_ini_contents)
        f.seek(0)

        initialize(config_file=f.name, log_file="stdout")


@pytest.mark.parametrize(
    "feature_flag,expect_warning", ((["django.instrumentation.inclusion-tags.r1"], False), (["noexist"], True))
)
def test_initialize_config_file_feature_flag(feature_flag, expect_warning, logger):
    settings = global_settings()
    apply_config_setting(settings, "feature_flag", feature_flag)
    _reset_configuration_done()

    with tempfile.NamedTemporaryFile() as f:
        f.write(newrelic_ini_contents)
        f.seek(0)

        initialize(config_file=f.name)

    message = (
        "Unknown agent feature flag 'noexist' provided. "
        "Check agent documentation or release notes, or "
        "contact New Relic support for clarification of "
        "validity of the specific feature flag."
    )
    if expect_warning:
        assert message in logger.caplog.records
    else:
        assert message not in logger.caplog.records

    apply_config_setting(settings, "feature_flag", [])


@pytest.mark.parametrize(
    "feature_flag,expect_warning", ((["django.instrumentation.inclusion-tags.r1"], False), (["noexist"], True))
)
def test_initialize_no_config_file_feature_flag(feature_flag, expect_warning, logger):
    settings = global_settings()
    apply_config_setting(settings, "feature_flag", feature_flag)
    _reset_configuration_done()

    initialize()

    message = (
        "Unknown agent feature flag 'noexist' provided. "
        "Check agent documentation or release notes, or "
        "contact New Relic support for clarification of "
        "validity of the specific feature flag."
    )

    if expect_warning:
        assert message in logger.caplog.records
    else:
        assert message not in logger.caplog.records

    apply_config_setting(settings, "feature_flag", [])


@pytest.mark.parametrize(
    "setting_name,setting_value,expect_error",
    (
        ("transaction_tracer.function_trace", [callable_name(function_to_trace)], False),
        ("transaction_tracer.generator_trace", [callable_name(function_to_trace)], False),
        ("transaction_tracer.function_trace", ["no_exist"], True),
        ("transaction_tracer.generator_trace", ["no_exist"], True),
    ),
)
def test_initialize_config_file_with_traces(setting_name, setting_value, expect_error, logger):
    settings = global_settings()
    apply_config_setting(settings, setting_name, setting_value)
    _reset_configuration_done()

    with tempfile.NamedTemporaryFile() as f:
        f.write(newrelic_ini_contents)
        f.seek(0)

        initialize(config_file=f.name)

    if expect_error:
        assert "CONFIGURATION ERROR" in logger.caplog.records
    else:
        assert "CONFIGURATION ERROR" not in logger.caplog.records

    apply_config_setting(settings, setting_name, [])


func_newrelic_ini = b"""
[function-trace:]
enabled = True
function = test_configuration:function_to_trace
name = function_to_trace
group = group
label = label
terminal = False
rollup = foo/all
"""

bad_func_newrelic_ini = b"""
[function-trace:]
enabled = True
function = function_to_trace
"""

func_missing_enabled_newrelic_ini = b"""
[function-trace:]
function = function_to_trace
"""

external_newrelic_ini = b"""
[external-trace:]
enabled = True
function = test_configuration:function_to_trace
library = "foo"
url = localhost:80/foo
method = GET
"""

bad_external_newrelic_ini = b"""
[external-trace:]
enabled = True
function = function_to_trace
"""

external_missing_enabled_newrelic_ini = b"""
[external-trace:]
function = function_to_trace
"""

generator_newrelic_ini = b"""
[generator-trace:]
enabled = True
function = test_configuration:function_to_trace
name = function_to_trace
group = group
"""

bad_generator_newrelic_ini = b"""
[generator-trace:]
enabled = True
function = function_to_trace
"""

generator_missing_enabled_newrelic_ini = b"""
[generator-trace:]
function = function_to_trace
"""

bg_task_newrelic_ini = b"""
[background-task:]
enabled = True
function = test_configuration:function_to_trace
lambda = test_configuration:function_to_trace
"""

bad_bg_task_newrelic_ini = b"""
[background-task:]
enabled = True
function = function_to_trace
"""

bg_task_missing_enabled_newrelic_ini = b"""
[background-task:]
function = function_to_trace
"""

db_trace_newrelic_ini = b"""
[database-trace:]
enabled = True
function = test_configuration:function_to_trace
sql = test_configuration:function_to_trace
"""

bad_db_trace_newrelic_ini = b"""
[database-trace:]
enabled = True
function = function_to_trace
"""

db_trace_missing_enabled_newrelic_ini = b"""
[database-trace:]
function = function_to_trace
"""

wsgi_newrelic_ini = b"""
[wsgi-application:]
enabled = True
function = test_configuration:function_to_trace
application = app
"""

bad_wsgi_newrelic_ini = b"""
[wsgi-application:]
enabled = True
function = function_to_trace
application = app
"""

wsgi_missing_enabled_newrelic_ini = b"""
[wsgi-application:]
function = function_to_trace
application = app
"""

wsgi_unparseable_enabled_newrelic_ini = b"""
[wsgi-application:]
enabled = not-a-bool
function = function_to_trace
application = app
"""


@pytest.mark.parametrize(
    "section,expect_error",
    (
        (func_newrelic_ini, False),
        (bad_func_newrelic_ini, True),
        (func_missing_enabled_newrelic_ini, False),
        (external_newrelic_ini, False),
        (bad_external_newrelic_ini, True),
        (external_missing_enabled_newrelic_ini, False),
        (generator_newrelic_ini, False),
        (bad_generator_newrelic_ini, True),
        (generator_missing_enabled_newrelic_ini, False),
        (bg_task_newrelic_ini, False),
        (bad_bg_task_newrelic_ini, True),
        (bg_task_missing_enabled_newrelic_ini, False),
        (db_trace_newrelic_ini, False),
        (bad_db_trace_newrelic_ini, True),
        (db_trace_missing_enabled_newrelic_ini, False),
        (wsgi_newrelic_ini, False),
        (bad_wsgi_newrelic_ini, True),
        (wsgi_missing_enabled_newrelic_ini, False),
        (wsgi_unparseable_enabled_newrelic_ini, True),
    ),
    ids=(
        "func_newrelic_ini",
        "bad_func_newrelic_ini",
        "func_missing_enabled_newrelic_ini",
        "external_newrelic_ini",
        "bad_external_newrelic_ini",
        "external_missing_enabled_newrelic_ini",
        "generator_newrelic_ini",
        "bad_generator_newrelic_ini",
        "generator_missing_enabled_newrelic_ini",
        "bg_task_newrelic_ini",
        "bad_bg_task_newrelic_ini",
        "bg_task_missing_enabled_newrelic_ini",
        "db_trace_newrelic_ini",
        "bad_db_trace_newrelic_ini",
        "db_trace_missing_enabled_newrelic_ini",
        "wsgi_newrelic_ini",
        "bad_wsgi_newrelic_ini",
        "wsgi_missing_enabled_newrelic_ini",
        "wsgi_unparseable_enabled_newrelic_ini",
    ),
)
def test_initialize_developer_mode(section, expect_error, logger):
    settings = global_settings()
    apply_config_setting(settings, "monitor_mode", False)
    apply_config_setting(settings, "developer_mode", True)
    _reset_configuration_done()
    _reset_instrumentation_done()
    _reset_config_parser()

    with tempfile.NamedTemporaryFile() as f:
        f.write(newrelic_ini_contents)
        f.write(section)
        f.seek(0)

        initialize(config_file=f.name)

    if expect_error:
        assert "CONFIGURATION ERROR" in logger.caplog.records
    else:
        assert "CONFIGURATION ERROR" not in logger.caplog.records


@pytest.mark.parametrize(
    "account_id,expected_account_id",
    (
        ("012345678901", 12345678901),
        ("0123456789.1", None),
        ("01234567890", None),
        ("01²345678901", None),
        ("0xb101010101", None),
        ("fooooooooooo", None),
    ),
)
def test_map_aws_account_id(account_id, expected_account_id, logger):
    message = f"Improper configuration. cloud.aws.account_id = {account_id} will be ignored because it is not a 12 digit number."

    return_val = _map_aws_account_id(account_id, logger)

    assert return_val == expected_account_id
    if not expected_account_id:
        assert message in logger.caplog.records


newrelic_toml_contents = b"""
[tool.newrelic]
app_name = "test11"
monitor_mode = true

[tool.newrelic.env.development]
app_name = "test11 (Development)"

[tool.newrelic.env.production]
app_name = "test11 (Production)"
log_level = "error"

[tool.newrelic.env.production.distributed_tracing]
enabled = false

[tool.newrelic.error_collector]
enabled = true
ignore_errors = ["module:name1", "module:name"]

[tool.newrelic.transaction_tracer]
enabled = true

[tool.newrelic.import-hook.django]
"instrumentation.scripts.django_admin" = ["stuff", "stuff2"]
"""


@SKIP_IF_NOT_PY311
def test_toml_parse_development():
    settings = global_settings()
    _reset_configuration_done()
    _reset_config_parser()
    _reset_instrumentation_done()

    with tempfile.NamedTemporaryFile(suffix=".toml") as f:
        f.write(newrelic_toml_contents)
        f.seek(0)

        initialize(config_file=f.name, environment="development")
        value = fetch_config_setting(settings, "app_name")
        assert value != "test11"
        value = fetch_config_setting(settings, "monitor_mode")
        assert value is True
        value = fetch_config_setting(settings, "error_collector")
        assert value.enabled is True
        assert value.ignore_classes[0] == "module:name1"
        assert value.ignore_classes[1] == "module:name"


@SKIP_IF_NOT_PY311
def test_toml_parse_production():
    settings = global_settings()
    _reset_configuration_done()
    _reset_config_parser()
    _reset_instrumentation_done()

    with tempfile.NamedTemporaryFile(suffix=".toml") as f:
        f.write(newrelic_toml_contents)
        f.seek(0)

        initialize(config_file=f.name, environment="production")
        value = fetch_config_setting(settings, "app_name")
        assert value == "test11 (Production)"
        value = fetch_config_setting(settings, "distributed_tracing")
        assert value.enabled is False


@pytest.mark.parametrize(
    "pathtype", [str, lambda s: s.encode("utf-8"), pathlib.Path], ids=["str", "bytes", "pathlib.Path"]
)
def test_config_file_path_types_ini(pathtype):
    settings = global_settings()
    _reset_configuration_done()
    _reset_config_parser()
    _reset_instrumentation_done()

    with tempfile.NamedTemporaryFile(suffix=".ini") as f:
        f.write(newrelic_ini_contents)
        f.seek(0)

        config_file = pathtype(f.name)
        initialize(config_file=config_file)
        value = fetch_config_setting(settings, "app_name")
        assert value == "Python Agent Test (agent_features)"


@pytest.mark.parametrize(
    "pathtype", [str, lambda s: s.encode("utf-8"), pathlib.Path], ids=["str", "bytes", "pathlib.Path"]
)
@SKIP_IF_NOT_PY311
def test_config_file_path_types_toml(pathtype):
    settings = global_settings()
    _reset_configuration_done()
    _reset_config_parser()
    _reset_instrumentation_done()

    with tempfile.NamedTemporaryFile(suffix=".toml") as f:
        f.write(newrelic_toml_contents)
        f.seek(0)

        config_file = pathtype(f.name)
        initialize(config_file=config_file)
        value = fetch_config_setting(settings, "app_name")
        assert value == "test11"


@pytest.fixture
def caplog_handler():
    class CaplogHandler(logging.StreamHandler):
        """
        To prevent possible issues with pytest's monkey patching
        use a custom Caplog handler to capture all records
        """

        def __init__(self, *args, **kwargs):
            self.records = []
            super().__init__(*args, **kwargs)

        def emit(self, record):
            self.records.append(self.format(record))

    return CaplogHandler()


@pytest.fixture
def logger(caplog_handler):
    _logger = logging.getLogger("newrelic.config")
    _logger.addHandler(caplog_handler)
    _logger.caplog = caplog_handler
    _logger.setLevel(logging.WARNING)
    yield _logger
    del caplog_handler.records[:]
    _logger.removeHandler(caplog_handler)
