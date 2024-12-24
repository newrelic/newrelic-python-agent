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

# 1. After adding monkeypatching, make sure the existing tests work
# 2. Add test to activate the application/tracer (in the case that application does not exist)

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from newrelic.api.transaction import add_custom_attribute

# from opentelemetry.sdk.trace.export import (
#     BatchSpanProcessor,
#     ConsoleSpanExporter,
# )


provider = TracerProvider()
# processor = BatchSpanProcessor(ConsoleSpanExporter())
# provider.add_span_processor(processor)
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
        "transaction.name": "OtherTransaction/Otel/foo",
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
        "transaction.name": "OtherTransaction/Otel/foo",
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
    exact_users={"NR function trace": "Branched from OTel"},
)
@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Function/test_traces:test_trace_with_otel_to_newrelic.<locals>.newrelic_function_trace",
        "transaction.name": "OtherTransaction/Otel/foo",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
)
def test_trace_with_otel_to_newrelic():
    tracer = trace.get_tracer("TracerProviderTestOtelToNewRelic")

    @function_trace()
    def newrelic_function_trace():
        # Add custom attributes to the span
        add_custom_attribute("NR function trace", "Branched from OTel")

    with tracer.start_as_current_span("foo"):
        newrelic_function_trace()


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
    exact_users={"OTel span": "Branched from NR"},
)
@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "test_traces:test_trace_with_newrelic_to_otel.<locals>.newrelic_background_task",
        "transaction.name": "OtherTransaction/Otel/foo",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
)
def test_trace_with_newrelic_to_otel():
    def otel_span():
        tracer = trace.get_tracer("TracerProviderTestNewRelicToOtel")
        with tracer.start_as_current_span("foo"):
            add_custom_attribute("OTel span", "Branched from NR")

    @background_task()
    def newrelic_background_task():
        otel_span()

    newrelic_background_task()
