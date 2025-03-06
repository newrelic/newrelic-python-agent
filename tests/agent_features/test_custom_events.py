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

import time

import pytest
from testing_support.fixtures import function_not_called, override_application_settings, reset_core_stats_engine
from testing_support.validators.validate_custom_event import (
    validate_custom_event_count,
    validate_custom_event_in_application_stats_engine,
)
from testing_support.validators.validate_custom_events import validate_custom_events

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction, record_custom_event
from newrelic.core.custom_event import process_event_type


def test_process_event_type_name_is_string():
    name = "string"
    assert process_event_type(name) == name


def test_process_event_type_name_is_not_string():
    name = 42
    assert process_event_type(name) is None


def test_process_event_type_name_ok_length():
    ok_name = "CustomEventType"
    assert process_event_type(ok_name) == ok_name


def test_process_event_type_name_too_long():
    too_long = "a" * 256
    assert process_event_type(too_long) is None


def test_process_event_type_name_valid_chars():
    valid_name = "az09: "
    assert process_event_type(valid_name) == valid_name


def test_process_event_type_name_invalid_chars():
    invalid_name = "&"
    assert process_event_type(invalid_name) is None


_now = time.time()

_intrinsics = {"type": "FooEvent", "timestamp": _now}
_user_params = {"foo": "bar"}
_event = [_intrinsics, _user_params]


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine(_event)
@background_task()
def test_add_custom_event_to_transaction_stats_engine_drops_none_attr():
    attrs = {"drop-me": None}
    attrs.update(_user_params)
    record_custom_event("FooEvent", attrs)


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine(_event)
def test_add_custom_event_to_application_stats_engine_drops_none_attr():
    attrs = {"drop-me": None}
    attrs.update(_user_params)

    app = application()
    record_custom_event("FooEvent", attrs, application=app)


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine(_event)
@background_task()
def test_add_custom_event_to_transaction_stats_engine():
    record_custom_event("FooEvent", _user_params)


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine(_event)
def test_add_custom_event_to_application_stats_engine():
    app = application()
    record_custom_event("FooEvent", _user_params, application=app)


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_custom_event_inside_transaction_bad_event_type():
    record_custom_event("!@#$%^&*()", {"foo": "bar"})


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_custom_event_outside_transaction_bad_event_type():
    app = application()
    record_custom_event("!@#$%^&*()", {"foo": "bar"}, application=app)


_mixed_params = {"foo": "bar", 123: "bad key"}


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine(_event)
@background_task()
def test_custom_event_inside_transaction_mixed_params():
    record_custom_event("FooEvent", _mixed_params)


@override_application_settings({"custom_insights_events.max_attribute_value": 4095})
@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine([_intrinsics, {"foo": "bar", "bar": "a" * 4095}])
@background_task()
def test_custom_event_inside_transaction_max_attribute_value():
    record_custom_event("FooEvent", {"foo": "bar", 123: "bad key", "bar": "a" * 5000})


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine([_intrinsics, {"foo": "bar", "bar": "a" * 255}])
@background_task()
def test_custom_event_inside_transaction_default_attribute_value():
    record_custom_event("FooEvent", {"foo": "bar", 123: "bad key", "bar": "a" * 5000})


@override_application_settings({"custom_insights_events.max_attribute_value": 4095})
@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine([_intrinsics, {"foo": "bar", "bar": "a" * 4095}])
def test_custom_event_outside_transaction_max_attribute_value():
    app = application()
    record_custom_event("FooEvent", {"foo": "bar", 123: "bad key", "bar": "a" * 5000}, application=app)


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine([_intrinsics, {"foo": "bar", "bar": "a" * 255}])
def test_custom_event_outside_transaction_default_attribute_value():
    app = application()
    record_custom_event("FooEvent", {"foo": "bar", 123: "bad key", "bar": "a" * 5000}, application=app)


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine(_event)
@background_task()
def test_custom_event_outside_transaction_mixed_params():
    app = application()
    record_custom_event("FooEvent", _mixed_params, application=app)


_bad_params = {"*" * 256: "too long", 123: "bad key"}
_event_with_no_params = [{"type": "FooEvent", "timestamp": _now}, {}]


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine(_event_with_no_params)
@background_task()
def test_custom_event_inside_transaction_bad_params():
    record_custom_event("FooEvent", _bad_params)


@reset_core_stats_engine()
@validate_custom_event_in_application_stats_engine(_event_with_no_params)
@background_task()
def test_custom_event_outside_transaction_bad_params():
    app = application()
    record_custom_event("FooEvent", _bad_params, application=app)


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_custom_event_params_not_a_dict():
    record_custom_event("ParamsListEvent", ["not", "a", "dict"])


# Tests for Custom Events configuration settings


@override_application_settings({"collect_custom_events": False})
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_custom_event_settings_check_collector_flag():
    record_custom_event("FooEvent", _user_params)


@override_application_settings({"custom_insights_events.enabled": False})
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_custom_event_settings_check_custom_insights_enabled():
    record_custom_event("FooEvent", _user_params)


# Test that record_custom_event() methods will short-circuit.
#
# If the custom_insights_events setting is False, verify that the
# `create_custom_event()` function is not called, in order to avoid the
# event_type and attribute processing.


@override_application_settings({"custom_insights_events.enabled": False})
@function_not_called("newrelic.api.transaction", "create_custom_event")
@background_task()
def test_transaction_create_custom_event_not_called():
    record_custom_event("FooEvent", _user_params)


@override_application_settings({"custom_insights_events.enabled": False})
@function_not_called("newrelic.core.application", "create_custom_event")
@background_task()
def test_application_create_custom_event_not_called():
    app = application()
    record_custom_event("FooEvent", _user_params, application=app)


# Test completness of LLM content/input despite attribute limits being set


@pytest.mark.parametrize(
    "event_type,event_data,expected_event_data",
    (
        [
            "LlmChatCompletionMessage",
            {"content": "A" * 9001, "input": "B" * 9001, "foo": f"b{'a' * 9000}r"},
            {"content": "A" * 9001, "input": "B" * 300, "foo": f"b{'a' * 299}"},
        ],
        [
            "LlmEmbedding",
            {"content": "A" * 9001, "input": "B" * 9001, "foo": f"b{'a' * 9000}r"},
            {"content": "A" * 300, "input": "B" * 9001, "foo": f"b{'a' * 299}"},
        ],
        [
            "MyCustomEvent",
            {"content": "A" * 9001, "input": "B" * 9001, "foo": f"b{'a' * 9000}r"},
            {"content": "A" * 300, "input": "B" * 300, "foo": f"b{'a' * 299}"},
        ],
    ),
)
def test_create_custom_event_no_limit(event_type, event_data, expected_event_data):
    @reset_core_stats_engine()
    @override_application_settings({"custom_insights_events.max_attribute_value": 300})
    @validate_custom_event_count(1)
    @validate_custom_events([({"type": event_type}, expected_event_data)])
    @background_task()
    def _test():
        transaction = current_transaction()
        transaction.record_custom_event(event_type, event_data)

    _test()
