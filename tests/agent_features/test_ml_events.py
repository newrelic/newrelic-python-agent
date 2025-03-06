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
from importlib import reload

import pytest
from testing_support.fixtures import function_not_called, override_application_settings, reset_core_stats_engine
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_event_payload import validate_ml_event_payload
from testing_support.validators.validate_ml_events import validate_ml_events
from testing_support.validators.validate_ml_events_outside_transaction import validate_ml_events_outside_transaction

import newrelic.core.otlp_utils
from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.transaction import record_ml_event
from newrelic.core.config import global_settings

_now = time.time()

_intrinsics = {"type": "LabelEvent", "timestamp": _now}


@pytest.fixture(scope="session")
def core_app(collector_agent_registration):
    app = collector_agent_registration
    return app._agent.application(app.name)


@validate_ml_event_payload(
    {
        "apm": [
            {
                "foo": "bar",
                "real_agent_id": "1234567",
                "event.domain": "newrelic.ml_events",
                "event.name": "MyCustomEvent",
            }
        ]
    }
)
@reset_core_stats_engine()
def test_ml_event_payload_noninference_event_inside_transaction(core_app):
    @background_task(name="test_ml_event_payload_inside_transaction")
    def _test():
        record_ml_event("MyCustomEvent", {"foo": "bar"})

    _test()
    core_app.harvest()


@validate_ml_event_payload(
    {
        "inference": [
            {
                "foo": "bar",
                "real_agent_id": "1234567",
                "event.domain": "newrelic.ml_events",
                "event.name": "InferenceEvent",
            }
        ]
    }
)
@reset_core_stats_engine()
def test_ml_event_payload_inference_event_inside_transaction(core_app):
    @background_task(name="test_ml_event_payload_inside_transaction")
    def _test():
        record_ml_event("InferenceEvent", {"foo": "bar"})

    _test()
    core_app.harvest()


@validate_ml_event_payload(
    {
        "apm": [
            {
                "foo": "bar",
                "real_agent_id": "1234567",
                "event.domain": "newrelic.ml_events",
                "event.name": "MyCustomEvent",
            }
        ],
        "inference": [
            {
                "foo": "bar",
                "real_agent_id": "1234567",
                "event.domain": "newrelic.ml_events",
                "event.name": "InferenceEvent",
            }
        ],
    }
)
@reset_core_stats_engine()
def test_ml_event_payload_both_events_inside_transaction(core_app):
    @background_task(name="test_ml_event_payload_inside_transaction")
    def _test():
        record_ml_event("InferenceEvent", {"foo": "bar"})
        record_ml_event("MyCustomEvent", {"foo": "bar"})

    _test()
    core_app.harvest()


@validate_ml_event_payload(
    {
        "inference": [
            {
                "foo": "bar",
                "real_agent_id": "1234567",
                "event.domain": "newrelic.ml_events",
                "event.name": "InferenceEvent",
            }
        ]
    }
)
@reset_core_stats_engine()
def test_ml_event_payload_inference_event_outside_transaction(core_app):
    def _test():
        app = application()
        record_ml_event("InferenceEvent", {"foo": "bar"}, application=app)

    _test()
    core_app.harvest()


@validate_ml_event_payload(
    {
        "apm": [
            {
                "foo": "bar",
                "real_agent_id": "1234567",
                "event.domain": "newrelic.ml_events",
                "event.name": "MyCustomEvent",
            }
        ],
        "inference": [
            {
                "foo": "bar",
                "real_agent_id": "1234567",
                "event.domain": "newrelic.ml_events",
                "event.name": "InferenceEvent",
            }
        ],
    }
)
@reset_core_stats_engine()
def test_ml_event_payload_both_events_outside_transaction(core_app):
    def _test():
        app = application()
        record_ml_event("InferenceEvent", {"foo": "bar"}, application=app)
        record_ml_event("MyCustomEvent", {"foo": "bar"}, application=app)

    _test()
    core_app.harvest()


@validate_ml_event_payload(
    {
        "apm": [
            {
                "foo": "bar",
                "real_agent_id": "1234567",
                "event.domain": "newrelic.ml_events",
                "event.name": "MyCustomEvent",
            }
        ]
    }
)
@reset_core_stats_engine()
def test_ml_event_payload_noninference_event_outside_transaction(core_app):
    def _test():
        app = application()
        record_ml_event("MyCustomEvent", {"foo": "bar"}, application=app)

    _test()
    core_app.harvest()


@pytest.mark.parametrize(
    "params,expected",
    [
        ({"foo": "bar"}, [(_intrinsics, {"foo": "bar"})]),
        ({"foo": "bar", 123: "bad key"}, [(_intrinsics, {"foo": "bar"})]),
        ({"foo": "bar", "*" * 256: "too long"}, [(_intrinsics, {"foo": "bar"})]),
    ],
    ids=["Valid key/value", "Bad key", "Value too long"],
)
@reset_core_stats_engine()
def test_record_ml_event_inside_transaction(params, expected):
    @validate_ml_events(expected)
    @background_task()
    def _test():
        record_ml_event("LabelEvent", params)

    _test()


@reset_core_stats_engine()
def test_record_ml_event_truncation_inside_transaction():
    @validate_ml_events([(_intrinsics, {"a": "a" * 4095})])
    @background_task()
    def _test():
        record_ml_event("LabelEvent", {"a": "a" * 4100})

    _test()


@reset_core_stats_engine()
def test_record_ml_event_truncation_outside_transaction():
    @validate_ml_events_outside_transaction([(_intrinsics, {"a": "a" * 4095})])
    def _test():
        app = application()
        record_ml_event("LabelEvent", {"a": "a" * 4100}, application=app)

    _test()


@reset_core_stats_engine()
def test_record_ml_event_max_num_attrs():
    too_many_attrs_event = {}
    for i in range(65):
        too_many_attrs_event[str(i)] = str(i)

    max_attrs_event = {}
    for i in range(64):
        max_attrs_event[str(i)] = str(i)

    @validate_ml_events([(_intrinsics, max_attrs_event)])
    @background_task()
    def _test():
        record_ml_event("LabelEvent", too_many_attrs_event)

    _test()


@reset_core_stats_engine()
def test_record_ml_event_max_num_attrs_outside_transaction():
    too_many_attrs_event = {}
    for i in range(65):
        too_many_attrs_event[str(i)] = str(i)

    max_attrs_event = {}
    for i in range(64):
        max_attrs_event[str(i)] = str(i)

    @validate_ml_events_outside_transaction([(_intrinsics, max_attrs_event)])
    def _test():
        app = application()
        record_ml_event("LabelEvent", too_many_attrs_event, application=app)

    _test()


@pytest.mark.parametrize(
    "params,expected",
    [
        ({"foo": "bar"}, [(_intrinsics, {"foo": "bar"})]),
        ({"foo": "bar", 123: "bad key"}, [(_intrinsics, {"foo": "bar"})]),
        ({"foo": "bar", "*" * 256: "too long"}, [(_intrinsics, {"foo": "bar"})]),
    ],
    ids=["Valid key/value", "Bad key", "Value too long"],
)
@reset_core_stats_engine()
def test_record_ml_event_outside_transaction(params, expected):
    @validate_ml_events_outside_transaction(expected)
    def _test():
        app = application()
        record_ml_event("LabelEvent", params, application=app)

    _test()


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
@background_task()
def test_record_ml_event_inside_transaction_bad_event_type():
    record_ml_event("!@#$%^&*()", {"foo": "bar"})


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_record_ml_event_outside_transaction_bad_event_type():
    app = application()
    record_ml_event("!@#$%^&*()", {"foo": "bar"}, application=app)


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
@background_task()
def test_record_ml_event_inside_transaction_params_not_a_dict():
    record_ml_event("ParamsListEvent", ["not", "a", "dict"])


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_record_ml_event_outside_transaction_params_not_a_dict():
    app = application()
    record_ml_event("ParamsListEvent", ["not", "a", "dict"], application=app)


# Tests for ML Events configuration settings


@override_application_settings({"ml_insights_events.enabled": False})
@reset_core_stats_engine()
@validate_ml_event_count(count=0)
@background_task()
def test_ml_event_settings_check_ml_insights_disabled():
    record_ml_event("FooEvent", {"foo": "bar"})


# Test that record_ml_event() methods will short-circuit.
#
# If the ml_insights_events setting is False, verify that the
# `create_ml_event()` function is not called, in order to avoid the
# event_type and attribute processing.


@override_application_settings({"ml_insights_events.enabled": False})
@reset_core_stats_engine()
@function_not_called("newrelic.api.transaction", "create_custom_event")
@background_task()
def test_transaction_create_ml_event_not_called():
    record_ml_event("FooEvent", {"foo": "bar"})


@override_application_settings({"ml_insights_events.enabled": False})
@reset_core_stats_engine()
@function_not_called("newrelic.core.application", "create_custom_event")
@background_task()
def test_application_create_ml_event_not_called():
    app = application()
    record_ml_event("FooEvent", {"foo": "bar"}, application=app)


@pytest.fixture(scope="module", autouse=True, params=["protobuf", "json"])
def otlp_content_encoding(request):
    _settings = global_settings()
    prev = _settings.debug.otlp_content_encoding
    _settings.debug.otlp_content_encoding = request.param
    reload(newrelic.core.otlp_utils)
    assert newrelic.core.otlp_utils.otlp_content_setting == request.param, "Content encoding mismatch."

    yield

    _settings.debug.otlp_content_encoding = prev
