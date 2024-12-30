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

# COME BACK TO THIS AND TEST WITH THE API AND SDK AND
# SEE IF THE MONKEY PATCHING WORKS IN ADDITION TO SETTING
# UP THE TRACER PROVIDER (which for NR should not do anything)

# 4. Add test to use `use_span` instead of `start_as_current_span`
# 5. Add test to use `use_span` instead of `start_as_current_span` while also employing a @function_trace decorator
# 6. Add test that uses two transactions (maybe start with otel and continue with NR function within a BG task)
# 7. Add test that adds Otel attributes to NR transaction and span

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from newrelic.api.time_trace import add_custom_span_attribute
from newrelic.api.transaction import add_custom_attribute

# from opentelemetry.sdk.trace.export import (
#     BatchSpanProcessor,
#     ConsoleSpanExporter,
# )
# processor = BatchSpanProcessor(ConsoleSpanExporter())
# provider.add_span_processor(processor)

provider = TracerProvider()
trace.set_tracer_provider(provider)


@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Otel/foo",
        "transaction.name": "OtherTransaction/Otel/foo",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
)
def test_trace_basic():
    tracer = trace.get_tracer("TracerProviderTestBasic")

    with tracer.start_as_current_span("foo"):
        pass


@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Otel/baz",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
)
@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Otel/bar",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
)
@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Otel/foo",
        "transaction.name": "OtherTransaction/Otel/foo",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
)
def test_trace_nested():
    """
    This test ensures that context propagation works as expected.
    """
    tracer = trace.get_tracer("TracerProviderTestNested")

    with tracer.start_as_current_span("foo"):
        with tracer.start_as_current_span("bar"):
            with tracer.start_as_current_span("baz"):
                pass


@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Otel/foo",
        "transaction.name": "OtherTransaction/Otel/foo",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
    exact_users={
        "NR custom transaction attribute": "Branched from OTel",
        "NR custom trace attribute": "OTel span",
    },
)
@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Function/test_traces:test_trace_with_otel_to_newrelic.<locals>.newrelic_function_trace",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
    exact_users={"NR custom trace attribute": "NR trace"},
)
def test_trace_with_otel_to_newrelic():
    """
    This test transitions from Otel to New Relic conventions and
    adds custom attributes to the transaction and trace
    (or trace and span in Otel terms).
    `add_custom_attribute` adds custom attributes to the transaction.
    `add_custom_span_attribute` adds custom attributes to the trace.
    Note that a transaction's custom attributes are added to the root
    span's user attributes.
    """
    tracer = trace.get_tracer("TracerProviderTestOtelToNewRelic")

    @function_trace()
    def newrelic_function_trace():
        add_custom_attribute("NR custom transaction attribute", "Branched from OTel")
        add_custom_span_attribute("NR custom trace attribute", "NR trace")

    with tracer.start_as_current_span("foo"):
        add_custom_span_attribute("NR custom trace attribute", "OTel span")
        newrelic_function_trace()


@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Otel/foo",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
    exact_users={"OTel span": "Branched from NR"},
)
@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Function/test_traces:test_trace_with_newrelic_to_otel.<locals>.newrelic_background_task",
        "transaction.name": "OtherTransaction/Function/test_traces:test_trace_with_newrelic_to_otel.<locals>.newrelic_background_task",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
)
def test_trace_with_newrelic_to_otel():
    """
    This test transitions from New Relic to Otel conventions and adds
    a custom span attribute from within the Otel span's context manager.
    """

    @background_task()
    def newrelic_background_task():
        tracer = trace.get_tracer("TracerProviderTestNewRelicToOtel")
        with tracer.start_as_current_span("foo"):
            add_custom_span_attribute("OTel span", "Branched from NR")

    newrelic_background_task()
