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

import os
import time

import pytest
import webtest
from testing_support.fixtures import (
    override_application_settings,
    override_generic_settings,
    reset_core_stats_engine,
    validate_attributes_complete,
    validate_custom_event_count,
    validate_custom_event_in_application_stats_engine,
    validate_request_params_omitted,
)
from testing_support.validators.validate_custom_parameters import (
    validate_custom_parameters,
)
from testing_support.validators.validate_non_transaction_error_event import (
    validate_non_transaction_error_event,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_tt_segment_params import (
    validate_tt_segment_params,
)

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.settings import STRIP_EXCEPTION_MESSAGE
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import (
    add_custom_attribute,
    capture_request_params,
    current_transaction,
    record_custom_event,
)
from newrelic.api.wsgi_application import wsgi_application
from newrelic.common.object_names import callable_name
from newrelic.config import apply_local_high_security_mode_setting
from newrelic.core.agent_protocol import AgentProtocol
from newrelic.core.attribute import (
    DST_ALL,
    DST_ERROR_COLLECTOR,
    DST_TRANSACTION_TRACER,
    Attribute,
)
from newrelic.core.config import Settings, apply_config_setting, global_settings


def test_hsm_configuration_default():
    # Global default should always be off.

    settings = global_settings()
    assert "NEW_RELIC_HIGH_SECURITY_MODE" not in os.environ
    assert settings.high_security is False


_hsm_local_config_file_settings_disabled = [
    {
        "high_security": False,
        "capture_params": True,
        "transaction_tracer.record_sql": "raw",
        "strip_exception_messages.enabled": False,
        "custom_insights_events.enabled": True,
        "message_tracer.segment_parameters_enabled": True,
        "application_logging.forwarding.enabled": True,
    },
    {
        "high_security": False,
        "capture_params": False,
        "transaction_tracer.record_sql": "raw",
        "strip_exception_messages.enabled": False,
        "custom_insights_events.enabled": False,
        "message_tracer.segment_parameters_enabled": True,
        "application_logging.forwarding.enabled": True,
    },
    {
        "high_security": False,
        "capture_params": False,
        "transaction_tracer.record_sql": "obfuscated",
        "strip_exception_messages.enabled": True,
        "custom_insights_events.enabled": True,
        "message_tracer.segment_parameters_enabled": False,
        "application_logging.forwarding.enabled": False,
    },
    {
        "high_security": False,
        "capture_params": False,
        "transaction_tracer.record_sql": "off",
        "strip_exception_messages.enabled": True,
        "custom_insights_events.enabled": False,
        "message_tracer.segment_parameters_enabled": False,
        "application_logging.forwarding.enabled": False,
    },
]

_hsm_local_config_file_settings_enabled = [
    {
        "high_security": True,
        "capture_params": True,
        "transaction_tracer.record_sql": "raw",
        "strip_exception_messages.enabled": True,
        "custom_insights_events.enabled": True,
        "message_tracer.segment_parameters_enabled": True,
        "application_logging.forwarding.enabled": False,
    },
    {
        "high_security": True,
        "capture_params": None,
        "transaction_tracer.record_sql": "raw",
        "strip_exception_messages.enabled": True,
        "custom_insights_events.enabled": True,
        "message_tracer.segment_parameters_enabled": True,
        "application_logging.forwarding.enabled": False,
    },
    {
        "high_security": True,
        "capture_params": True,
        "transaction_tracer.record_sql": "raw",
        "strip_exception_messages.enabled": True,
        "custom_insights_events.enabled": True,
        "message_tracer.segment_parameters_enabled": True,
        "application_logging.forwarding.enabled": False,
    },
    {
        "high_security": True,
        "capture_params": False,
        "transaction_tracer.record_sql": "raw",
        "strip_exception_messages.enabled": True,
        "custom_insights_events.enabled": True,
        "message_tracer.segment_parameters_enabled": True,
        "application_logging.forwarding.enabled": True,
    },
    {
        "high_security": True,
        "capture_params": True,
        "transaction_tracer.record_sql": "obfuscated",
        "strip_exception_messages.enabled": True,
        "custom_insights_events.enabled": True,
        "message_tracer.segment_parameters_enabled": True,
        "application_logging.forwarding.enabled": True,
    },
    {
        "high_security": True,
        "capture_params": True,
        "transaction_tracer.record_sql": "off",
        "strip_exception_messages.enabled": True,
        "custom_insights_events.enabled": True,
        "message_tracer.segment_parameters_enabled": False,
        "application_logging.forwarding.enabled": True,
    },
    {
        "high_security": True,
        "capture_params": True,
        "transaction_tracer.record_sql": "raw",
        "strip_exception_messages.enabled": False,
        "custom_insights_events.enabled": False,
        "message_tracer.segment_parameters_enabled": False,
        "application_logging.forwarding.enabled": True,
    },
]


def parameterize_hsm_local_config(settings_list):
    settings_object_list = []

    for settings in settings_list:
        settings_object = Settings()
        for name, value in settings.items():
            apply_config_setting(settings_object, name, value)
        settings_object_list.append(settings_object)

    return pytest.mark.parametrize("settings", settings_object_list)


@parameterize_hsm_local_config(_hsm_local_config_file_settings_disabled)
def test_local_config_file_override_hsm_disabled(settings):
    original_capture_params = settings.capture_params
    original_record_sql = settings.transaction_tracer.record_sql
    original_strip_messages = settings.strip_exception_messages.enabled
    original_custom_events = settings.custom_insights_events.enabled
    original_message_segment_params_enabled = settings.message_tracer.segment_parameters_enabled
    original_application_logging_forwarding_enabled = settings.application_logging.forwarding.enabled

    apply_local_high_security_mode_setting(settings)

    assert settings.capture_params == original_capture_params
    assert settings.transaction_tracer.record_sql == original_record_sql
    assert settings.strip_exception_messages.enabled == original_strip_messages
    assert settings.custom_insights_events.enabled == original_custom_events
    assert settings.message_tracer.segment_parameters_enabled == original_message_segment_params_enabled
    assert settings.application_logging.forwarding.enabled == original_application_logging_forwarding_enabled


@parameterize_hsm_local_config(_hsm_local_config_file_settings_enabled)
def test_local_config_file_override_hsm_enabled(settings):
    apply_local_high_security_mode_setting(settings)

    assert settings.capture_params not in (True, None)
    assert settings.transaction_tracer.record_sql in ("off", "obfuscated")
    assert settings.strip_exception_messages.enabled
    assert settings.custom_insights_events.enabled is False
    assert settings.message_tracer.segment_parameters_enabled is False
    assert settings.application_logging.forwarding.enabled is False


_server_side_config_settings_hsm_disabled = [
    (
        {
            "high_security": False,
            "capture_params": False,
            "transaction_tracer.record_sql": "obfuscated",
            "strip_exception_messages.enabled": True,
            "custom_insights_events.enabled": False,
            "application_logging.forwarding.enabled": False,
        },
        {
            "agent_config": {
                "capture_params": True,
                "transaction_tracer.record_sql": "raw",
                "strip_exception_messages.enabled": False,
                "custom_insights_events.enabled": True,
                "application_logging.forwarding.enabled": True,
            },
        },
    ),
    (
        {
            "high_security": False,
            "capture_params": True,
            "transaction_tracer.record_sql": "raw",
            "strip_exception_messages.enabled": False,
            "custom_insights_events.enabled": True,
            "application_logging.forwarding.enabled": True,
        },
        {
            "agent_config": {
                "capture_params": False,
                "transaction_tracer.record_sql": "off",
                "strip_exception_messages.enabled": True,
                "custom_insights_events.enabled": False,
                "application_logging.forwarding.enabled": False,
            },
        },
    ),
]

_server_side_config_settings_hsm_enabled = [
    (
        {
            "high_security": True,
            "capture_params": False,
            "transaction_tracer.record_sql": "obfuscated",
            "strip_exception_messages.enabled": True,
            "custom_insights_events.enabled": False,
            "application_logging.forwarding.enabled": False,
        },
        {
            "high_security": True,
            "capture_params": False,
            "transaction_tracer.record_sql": "obfuscated",
            "strip_exception_messages.enabled": True,
            "custom_insights_events.enabled": False,
            "application_logging.forwarding.enabled": False,
            "agent_config": {
                "capture_params": False,
                "transaction_tracer.record_sql": "obfuscated",
                "strip_exception_messages.enabled": True,
                "custom_insights_events.enabled": False,
                "application_logging.forwarding.enabled": False,
            },
        },
    ),
    (
        {
            "high_security": True,
            "capture_params": False,
            "transaction_tracer.record_sql": "obfuscated",
            "strip_exception_messages.enabled": True,
            "custom_insights_events.enabled": False,
            "application_logging.forwarding.enabled": False,
        },
        {
            "high_security": True,
            "capture_params": False,
            "transaction_tracer.record_sql": "obfuscated",
            "strip_exception_messages.enabled": True,
            "custom_insights_events.enabled": False,
            "application_logging.forwarding.enabled": False,
            "agent_config": {
                "capture_params": True,
                "transaction_tracer.record_sql": "raw",
                "strip_exception_messages.enabled": False,
                "custom_insights_events.enabled": True,
                "application_logging.forwarding.enabled": True,
            },
        },
    ),
]


@pytest.mark.parametrize("local_settings,server_settings", _server_side_config_settings_hsm_disabled)
def test_remote_config_fixups_hsm_disabled(local_settings, server_settings):
    assert "high_security" in local_settings
    assert local_settings["high_security"] is False

    assert "high_security" not in server_settings

    agent_config = server_settings["agent_config"]

    original_capture_params = agent_config["capture_params"]
    original_record_sql = agent_config["transaction_tracer.record_sql"]
    original_strip_messages = agent_config["strip_exception_messages.enabled"]
    original_custom_events = agent_config["custom_insights_events.enabled"]
    original_log_forwarding = agent_config["application_logging.forwarding.enabled"]

    _settings = global_settings()
    settings = override_generic_settings(_settings, local_settings)(AgentProtocol._apply_high_security_mode_fixups)(
        server_settings, _settings
    )

    agent_config = settings["agent_config"]

    assert "high_security" not in settings

    assert agent_config["capture_params"] == original_capture_params
    assert agent_config["transaction_tracer.record_sql"] == original_record_sql
    assert agent_config["strip_exception_messages.enabled"] == original_strip_messages
    assert agent_config["custom_insights_events.enabled"] == original_custom_events
    assert agent_config["application_logging.forwarding.enabled"] == original_log_forwarding


@pytest.mark.parametrize("local_settings,server_settings", _server_side_config_settings_hsm_enabled)
def test_remote_config_fixups_hsm_enabled(local_settings, server_settings):
    assert "high_security" in local_settings
    assert local_settings["high_security"] is True

    assert "high_security" in server_settings

    _settings = global_settings()
    settings = override_generic_settings(_settings, local_settings)(AgentProtocol._apply_high_security_mode_fixups)(
        server_settings, _settings
    )

    agent_config = settings["agent_config"]

    assert "high_security" not in settings
    assert "capture_params" not in settings
    assert "transaction_tracer.record_sql" not in settings
    assert "strip_exception_messages.enabled" not in settings
    assert "custom_insights_events.enabled" not in settings
    assert "application_logging.forwarding.enabled" not in settings

    assert "capture_params" not in agent_config
    assert "transaction_tracer.record_sql" not in agent_config
    assert "strip_exception_messages.enabled" not in agent_config
    assert "custom_insights_events.enabled" not in agent_config
    assert "application_logging.forwarding.enabled" not in agent_config


def test_remote_config_hsm_fixups_server_side_disabled():
    local_settings = {"high_security": True}
    server_settings = {"high_security": True}

    _settings = global_settings()
    settings = override_generic_settings(_settings, local_settings)(AgentProtocol._apply_high_security_mode_fixups)(
        server_settings, _settings
    )

    assert "high_security" not in settings


_test_transaction_settings_hsm_disabled = {"high_security": False}

# Normally, in HSM the exception message would be stripped just by turning on
# high_security. However, these tests (like all of our tests) overrides the
# settings after agent initialization where this setting is fixed up.

_test_transaction_settings_hsm_enabled = {
    "high_security": True,
    "strip_exception_messages.enabled": True,
    "custom_insights_events.enabled": False,
}


@override_application_settings(_test_transaction_settings_hsm_disabled)
@validate_custom_parameters(required_params=[("key", "value")])
@background_task()
def test_other_transaction_custom_parameters_hsm_disabled():
    add_custom_attribute("key", "value")


@override_application_settings(_test_transaction_settings_hsm_disabled)
@validate_custom_parameters(required_params=[("key-1", "value-1"), ("key-2", "value-2")])
@background_task()
def test_other_transaction_multiple_custom_parameters_hsm_disabled():
    transaction = current_transaction()
    transaction.add_custom_attributes([("key-1", "value-1"), ("key-2", "value-2")])


@override_application_settings(_test_transaction_settings_hsm_enabled)
@validate_custom_parameters(forgone_params=[("key", "value")])
@background_task()
def test_other_transaction_custom_parameters_hsm_enabled():
    add_custom_attribute("key", "value")


@override_application_settings(_test_transaction_settings_hsm_enabled)
@validate_custom_parameters(forgone_params=[("key-1", "value-1"), ("key-2", "value-2")])
@background_task()
def test_other_transaction_multiple_custom_parameters_hsm_enabled():
    transaction = current_transaction()
    transaction.add_custom_attributes([("key-1", "value-1"), ("key-2", "value-2")])


class TestException(Exception):
    pass


_test_exception_name = "%s:%s" % (__name__, TestException.__name__)


@override_application_settings(_test_transaction_settings_hsm_disabled)
@validate_transaction_errors(errors=[(_test_exception_name, "test message")], required_params=[("key-2", "value-2")])
@validate_custom_parameters(required_params=[("key-1", "value-1")])
@background_task()
def test_other_transaction_error_parameters_hsm_disabled():
    add_custom_attribute("key-1", "value-1")
    try:
        raise TestException("test message")
    except Exception:
        notice_error(attributes={"key-2": "value-2"})


@override_application_settings(_test_transaction_settings_hsm_enabled)
@validate_transaction_errors(
    errors=[(_test_exception_name, STRIP_EXCEPTION_MESSAGE)], forgone_params=[("key-2", "value-2")]
)
@validate_custom_parameters(forgone_params=[("key-1", "value-1")])
@background_task()
def test_other_transaction_error_parameters_hsm_enabled():
    add_custom_attribute("key-1", "value-1")
    try:
        raise TestException("test message")
    except Exception:
        notice_error(attributes={"key-2": "value-2"})


_err_message = "Error! :("
_intrinsic_attributes = {
    "error.class": callable_name(TestException),
    "error.message": _err_message,
    "error.expected": False,
}


@reset_core_stats_engine()
@override_application_settings(_test_transaction_settings_hsm_disabled)
@validate_non_transaction_error_event(required_intrinsics=_intrinsic_attributes, required_user={"key-1": "value-1"})
def test_non_transaction_error_parameters_hsm_disabled():
    try:
        raise TestException(_err_message)
    except Exception:
        app = application()
        notice_error(attributes={"key-1": "value-1"}, application=app)


_intrinsic_attributes = {
    "error.class": callable_name(TestException),
    "error.message": STRIP_EXCEPTION_MESSAGE,
    "error.expected": False,
}


@reset_core_stats_engine()
@override_application_settings(_test_transaction_settings_hsm_enabled)
@validate_non_transaction_error_event(required_intrinsics=_intrinsic_attributes, forgone_user={"key-1": "value-1"})
def test_non_transaction_error_parameters_hsm_enabled():
    try:
        raise TestException(_err_message)
    except Exception:
        app = application()
        notice_error(attributes={"key-1": "value-1"}, application=app)


@wsgi_application()
def target_wsgi_application_capture_params(environ, start_response):
    status = "200 OK"
    output = b"Hello World!"

    response_headers = [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(output)))]
    start_response(status, response_headers)

    return [output]


@wsgi_application()
def target_wsgi_application_capture_params_api_called(environ, start_response):
    status = "200 OK"
    output = b"Hello World!"

    capture_request_params(True)
    response_headers = [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(output)))]
    start_response(status, response_headers)

    return [output]


_test_transaction_settings_hsm_enabled_capture_params = {"high_security": True, "capture_params": False}


@override_application_settings(_test_transaction_settings_hsm_enabled_capture_params)
@validate_request_params_omitted()
def test_transaction_hsm_enabled_environ_capture_request_params():
    target_application = webtest.TestApp(target_wsgi_application_capture_params)

    target_application.get("/", params="key-1=value-1")


@override_application_settings(_test_transaction_settings_hsm_enabled_capture_params)
@validate_request_params_omitted()
def test_transaction_hsm_enabled_environ_capture_request_params_disabled():
    target_application = webtest.TestApp(target_wsgi_application_capture_params)

    environ = {}
    environ["newrelic.capture_request_params"] = False

    target_application.get("/", params="key-1=value-1", extra_environ=environ)


@override_application_settings(_test_transaction_settings_hsm_enabled_capture_params)
@validate_request_params_omitted()
def test_transaction_hsm_enabled_environ_capture_request_params_enabled():
    target_application = webtest.TestApp(target_wsgi_application_capture_params)

    environ = {}
    environ["newrelic.capture_request_params"] = True

    target_application.get("/", params="key-1=value-1", extra_environ=environ)


@override_application_settings(_test_transaction_settings_hsm_enabled_capture_params)
@validate_request_params_omitted()
def test_transaction_hsm_enabled_environ_capture_request_params_api_called():
    target_application = webtest.TestApp(target_wsgi_application_capture_params_api_called)

    target_application.get("/", params="key-1=value-1")


# Custom events

_event_type = "SimpleAppEvent"
_params = {"snowman": "\u2603", "foo": "bar"}


@wsgi_application()
def simple_custom_event_app(environ, start_response):
    record_custom_event(_event_type, _params)
    start_response(status="200 OK", response_headers=[])
    return []


_intrinsics = {"type": _event_type, "timestamp": time.time()}

_required_event = [_intrinsics, _params]


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine(_required_event)
@override_application_settings(_test_transaction_settings_hsm_disabled)
def test_custom_event_hsm_disabled():
    target_application = webtest.TestApp(simple_custom_event_app)
    target_application.get("/")


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@override_application_settings(_test_transaction_settings_hsm_enabled)
def test_custom_event_hsm_enabled():
    target_application = webtest.TestApp(simple_custom_event_app)
    target_application.get("/")


# Make sure we don't display the query string in 'request.headers.referer'
# Attribute will exist, and value will have query string stripped off.

_required_attr = Attribute(
    name="request.headers.referer",
    value="http://example.com/blah",
    destinations=DST_TRANSACTION_TRACER | DST_ERROR_COLLECTOR,
)

# Check that the unsanitized version isn't present either, for any
# destinations.

_forgone_attr = Attribute(
    name="request.headers.referer", value="http://example.com/blah?query=value", destinations=DST_ALL
)

_required_attrs = [_required_attr]
_foregone_attrs = [_forgone_attr]


@override_application_settings(_test_transaction_settings_hsm_enabled_capture_params)
@validate_attributes_complete("agent", _required_attrs, _foregone_attrs)
def test_http_referrer_url_is_sanitized_in_hsm():
    target_application = webtest.TestApp(target_wsgi_application_capture_params)

    environ = {}
    environ["HTTP_REFERER"] = "http://example.com/blah?query=value"

    target_application.get("/", extra_environ=environ)


@pytest.mark.parametrize("hsm_enabled", [True, False])
def test_function_trace_params_dropped_in_hsm(hsm_enabled):
    @background_task()
    def _test():
        with FunctionTrace("trace", params={"secret": "super secret"}):
            pass

    if hsm_enabled:
        _test = override_application_settings(_test_transaction_settings_hsm_enabled_capture_params)(_test)
        _test = validate_tt_segment_params(forgone_params=("secret",))(_test)
    else:
        _test = override_application_settings(_test_transaction_settings_hsm_disabled)(_test)
        _test = validate_tt_segment_params(present_params=("secret",))(_test)

    _test()


@pytest.mark.parametrize("hsm_enabled", [True, False])
def test_message_trace_params_dropped_in_hsm(hsm_enabled):
    @background_task()
    def _test():
        with MessageTrace("library", "operation", "dest_type", "dest_name", params={"secret": "super secret"}):
            pass

    if hsm_enabled:
        _test = override_application_settings(_test_transaction_settings_hsm_enabled_capture_params)(_test)
        _test = validate_tt_segment_params(forgone_params=("secret",))(_test)
    else:
        _test = override_application_settings(_test_transaction_settings_hsm_disabled)(_test)
        _test = validate_tt_segment_params(present_params=("secret",))(_test)

    _test()
