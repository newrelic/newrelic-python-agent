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
from opentelemetry import trace
from testing_support.fixtures import dt_enabled, override_application_settings
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from newrelic.api.time_trace import add_custom_span_attribute
from newrelic.api.transaction import add_custom_attribute


def test_trace_with_span_attributes(tracer):
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_intrinsics={
            "name": "Function/test_attributes:test_trace_with_span_attributes.<locals>._test",
            "transaction.name": "OtherTransaction/Function/test_attributes:test_trace_with_span_attributes.<locals>._test",
            "sampled": True,
        },
    )
    @validate_span_events(
        count=1,
        exact_intrinsics={"name": "Function/opentelemetry_span", "sampled": True},
        expected_intrinsics={"priority": None, "traceId": None, "guid": None},
        exact_users={"opentelemetry_attribute": "bar", "nr_attribute": "foo"},
    )
    @background_task()
    def _test():
        with tracer.start_as_current_span("opentelemetry_span", attributes={"opentelemetry_attribute": "bar"}):
            add_custom_span_attribute("nr_attribute", "foo")

    _test()


def test_trace_with_opentelemetry_to_newrelic(tracer):
    """
    This test adds custom attributes to the transaction and trace.
    * `add_custom_attribute` adds custom attributes to the transaction.
    * `add_custom_span_attribute` adds custom attributes to the trace.
    NOTE:
    1. Distinction between trace and span attributes is given for
    whether they are added to the transaction or the span.  A
    transaction's custom attributes are added to the root span's
    user attributes.
    2. Notation for attributes:
       - NR trace attributes: "NR_trace_attribute_<context>"
       - NR span attributes: "NR_span_attribute_<context>"
       - OpenTelemetry span attributes: "opentelemetry_span_attribute_<context>"
    Where <context> is either `FT` or `BG`, for FunctionTrace
    or BackgroundTask, respectively.
    """

    @function_trace()
    def newrelic_function_trace():
        add_custom_attribute("NR_trace_attribute_FT", "NR trace attribute from FT")
        add_custom_span_attribute("NR_span_attribute_FT", "NR span attribute from FT")
        opentelemetry_span = trace.get_current_span()
        opentelemetry_span.set_attribute("opentelemetry_span_attribute_FT", "OpenTelemetry span attribute from FT")

    @dt_enabled
    @validate_span_events(
        count=1,
        exact_intrinsics={
            "name": "Function/test_attributes:test_trace_with_opentelemetry_to_newrelic.<locals>.newrelic_background_task",
            "transaction.name": "OtherTransaction/Function/test_attributes:test_trace_with_opentelemetry_to_newrelic.<locals>.newrelic_background_task",
            "sampled": True,
        },
        exact_users={"NR_trace_attribute_FT": "NR trace attribute from FT"},
    )
    @validate_span_events(
        count=1,
        exact_intrinsics={"name": "Function/foo", "sampled": True},
        expected_intrinsics={"priority": None, "traceId": None, "guid": None},
        exact_users={
            "NR_span_attribute_BG": "NR span attribute from BG",
            "opentelemetry_span_attribute_BG": "OpenTelemetry span attribute from BG",
        },
    )
    @validate_span_events(
        count=1,
        exact_intrinsics={
            "name": "Function/test_attributes:test_trace_with_opentelemetry_to_newrelic.<locals>.newrelic_function_trace",
            "sampled": True,
        },
        exact_users={
            "NR_span_attribute_FT": "NR span attribute from FT",
            "opentelemetry_span_attribute_FT": "OpenTelemetry span attribute from FT",
        },
    )
    @background_task()
    def newrelic_background_task():
        with tracer.start_as_current_span("foo") as opentelemetry_span:
            add_custom_span_attribute("NR_span_attribute_BG", "NR span attribute from BG")
            opentelemetry_span.set_attribute("opentelemetry_span_attribute_BG", "OpenTelemetry span attribute from BG")
            newrelic_function_trace()

    newrelic_background_task()


@pytest.mark.parametrize(
    "untruncated_attributes,expected_length",
    [
        # The connect response lists this attribute, so it is never truncated.
        (frozenset({"gen_ai.input.messages"}), 5000),
        # Without the connect response listing it, the default attribute limit applies.
        (frozenset(), 255),
    ],
)
def test_untruncated_span_attributes(tracer, untruncated_attributes, expected_length):
    @override_application_settings({"opentelemetry._untruncated_attributes": untruncated_attributes})
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_intrinsics={"name": "Function/opentelemetry_span"},
        # Attributes that are not listed are always truncated.
        exact_users={"gen_ai.input.messages": "a" * expected_length, "other_attribute": "b" * 255},
    )
    @background_task()
    def _test():
        with tracer.start_as_current_span(
            "opentelemetry_span", attributes={"gen_ai.input.messages": "a" * 5000, "other_attribute": "b" * 1000}
        ):
            pass

    _test()


def test_untruncated_attributes_only_apply_to_opentelemetry_spans():
    @function_trace(name="nr_function")
    def nr_function():
        add_custom_span_attribute("gen_ai.input.messages", "a" * 5000)

    @override_application_settings({"opentelemetry._untruncated_attributes": frozenset({"gen_ai.input.messages"})})
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_intrinsics={"name": "Function/nr_function"},
        # A listed attribute on a span that did not come from OpenTelemetry is still truncated.
        exact_users={"gen_ai.input.messages": "a" * 255},
    )
    @background_task()
    def _test():
        nr_function()

    _test()


def test_update_name(tracer):
    @dt_enabled
    @validate_span_events(
        count=1,
        exact_intrinsics={
            "name": "Function/test_attributes:test_update_name.<locals>._test",
            "transaction.name": "OtherTransaction/Function/test_attributes:test_update_name.<locals>._test",
        },
    )
    @background_task()
    def _test():
        span = tracer.start_span("initial_span_name")
        assert span.name == "initial_span_name"

        span.update_name("updated_span_name")
        assert span.name == "updated_span_name"

        span.end()

    _test()
