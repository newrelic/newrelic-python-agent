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

from opentelemetry import trace
from testing_support.fixtures import dt_enabled
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
        exact_intrinsics={"name": "Function/otelspan", "sampled": True},
        expected_intrinsics={"priority": None, "traceId": None, "guid": None},
        exact_users={"otel_attribute": "bar", "nr_attribute": "foo"},
    )
    @background_task()
    def _test():
        with tracer.start_as_current_span("otelspan", attributes={"otel_attribute": "bar"}):
            add_custom_span_attribute("nr_attribute", "foo")

    _test()


def test_trace_with_otel_to_newrelic(tracer):
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
       - OTel span attributes: "otel_span_attribute_<context>"
    Where <context> is either `FT` or `BG`, for FunctionTrace
    or BackgroundTask, respectively.
    """

    @function_trace()
    def newrelic_function_trace():
        add_custom_attribute("NR_trace_attribute_FT", "NR trace attribute from FT")
        add_custom_span_attribute("NR_span_attribute_FT", "NR span attribute from FT")
        otel_span = trace.get_current_span()
        otel_span.set_attribute("otel_span_attribute_FT", "OTel span attribute from FT")

    @dt_enabled
    @validate_span_events(
        count=1,
        exact_intrinsics={
            "name": "Function/test_attributes:test_trace_with_otel_to_newrelic.<locals>.newrelic_background_task",
            "transaction.name": "OtherTransaction/Function/test_attributes:test_trace_with_otel_to_newrelic.<locals>.newrelic_background_task",
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
            "otel_span_attribute_BG": "OTel span attribute from BG",
        },
    )
    @validate_span_events(
        count=1,
        exact_intrinsics={
            "name": "Function/test_attributes:test_trace_with_otel_to_newrelic.<locals>.newrelic_function_trace",
            "sampled": True,
        },
        exact_users={
            "NR_span_attribute_FT": "NR span attribute from FT",
            "otel_span_attribute_FT": "OTel span attribute from FT",
        },
    )
    @background_task()
    def newrelic_background_task():
        with tracer.start_as_current_span("foo") as otel_span:
            add_custom_span_attribute("NR_span_attribute_BG", "NR span attribute from BG")
            otel_span.set_attribute("otel_span_attribute_BG", "OTel span attribute from BG")
            newrelic_function_trace()

    newrelic_background_task()
