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

import pytest
from testing_support.fixtures import override_application_settings, reset_core_stats_engine
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_event_attributes import validate_error_event_attributes
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_events import validate_log_events

from newrelic.api.background_task import background_task

# Log Event Tests


@override_application_settings({"application_logging.forwarding.enabled": True})
@validate_log_events([{"message": "otel_event"}])
def test_events_as_logs(tracer):
    @background_task()
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            otel_span.add_event("otel_event")

    _test()


@pytest.mark.parametrize("name", [{"dict": "value"}, ["list", "of", "values"], 42, None])
@override_application_settings({"application_logging.forwarding.enabled": True})
@validate_log_event_count(0)
def test_events_as_logs_with_bad_name_argument(tracer, name):
    _exact_attrs = {
        "agent": {},
        "user": {"exception.escaped": False},
        "intrinsic": {
            "error.class": "builtins:ValueError",
            "error.message": "Event name is required and must be a string.",
            "error.expected": False,
            "transactionName": "OtherTransaction/Function/test_events:test_events_as_logs_with_bad_name_argument.<locals>._test",
        },
    }

    @validate_error_event_attributes(exact_attrs=_exact_attrs)
    @background_task()
    def _test():
        with pytest.raises(ValueError):
            with tracer.start_as_current_span("otelspan") as otel_span:
                otel_span.add_event(name)

    _test()


# While NR has the ability to record log events outside of
# a transaction, the Hybrid Agent does not.  The span created
# here will be a NonRecordingSpan and thus the event will
# not be recorded.
@override_application_settings({"application_logging.forwarding.enabled": True})
@validate_log_event_count(0)
def test_events_as_logs_outside_transaction(tracer):
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            otel_span.add_event("otel_event")

    _test()


# Custom Event Tests

_event_attributes = {"key1": "value1", "key2": 42}


@reset_core_stats_engine()
@validate_custom_events([({"type": "otel_event"}, _event_attributes)])
def test_events_as_custom_events(tracer):
    @background_task()
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            otel_span.add_event("otel_event", attributes=_event_attributes)

    _test()


# Instead of falling back to recording a log event when the
# attributes argument is invalid, a ValueError is raised.
# This is to ensure that the developer is aware that their
# event is not being recorded as intended.
@pytest.mark.parametrize("attributes", ["string", ["list", "of", "values"], 42])
@reset_core_stats_engine()
@validate_log_event_count(0)
@validate_custom_event_count(0)
def test_events_as_custom_events_with_bad_attributes_argument(tracer, attributes):
    _exact_attrs = {
        "agent": {},
        "user": {"exception.escaped": False},
        "intrinsic": {
            "error.class": "builtins:ValueError",
            "error.message": "Event attributes must be a dictionary.",
            "error.expected": False,
            "transactionName": "OtherTransaction/Function/test_events:test_events_as_custom_events_with_bad_attributes_argument.<locals>._test",
        },
    }

    @validate_error_event_attributes(exact_attrs=_exact_attrs)
    @background_task()
    def _test():
        with pytest.raises(ValueError):
            with tracer.start_as_current_span("otelspan") as otel_span:
                otel_span.add_event("otel_event", attributes=attributes)

    _test()


# While NR has the ability to record custom events outside of
# a transaction, the Hybrid Agent does not.  The span created
# here will be a NonRecordingSpan and thus the event will
# not be recorded.
@reset_core_stats_engine()
@validate_custom_event_count(0)
def test_events_as_custom_events_outside_transaction(tracer):
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            otel_span.add_event("otel_event", attributes=_event_attributes)

    _test()
