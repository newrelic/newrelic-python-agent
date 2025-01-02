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
# TODO: Add tests to see if processors and exporters work as expected.

provider = TracerProvider()
trace.set_tracer_provider(provider)


@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Otel/otelspan",
        "transaction.name": "OtherTransaction/Otel/otelspan",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
)
def test_trace_basic():
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("otelspan"):
        pass


@validate_span_events(
    count=1,
    exact_intrinsics={
        "name": "Otel/otelspan",
        "transaction.name": "OtherTransaction/Otel/otelspan",
        "sampled": True,
    },
    expected_intrinsics={
        "priority": None,
        "traceId": None,
        "guid": None,
    },
    exact_users={
        "otel_attribute": "bar",
        "nr_attribute": "foo",
    },
)
def test_trace_with_attributes():
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("otelspan", attributes={"otel_attribute": "bar"}):
        add_custom_span_attribute("nr_attribute", "foo")


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
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("foo"):
        with tracer.start_as_current_span("bar"):
            with tracer.start_as_current_span("baz"):
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
def test_trace_nested_with_decorators():
    """
    This test ensures that context propagation works as expected.
    """
    tracer = trace.get_tracer(__name__)

    @tracer.start_as_current_span("foo")
    @tracer.start_as_current_span("bar")
    @tracer.start_as_current_span("baz")
    def _test():
        pass

    _test()


def test_trace_nested_with_use_span():
    """
    Another test to ensure proper context propagation by
    checking the following:
    1. The validity of the following instrumentation methods:
        a. `trace.get_current_span()`
        b. `trace.use_span()`
    2. That a mix of NR and Otel functions can be used together.
    3. That proper child/parent relationships are maintained.
    """

    @function_trace()
    def new_relic_function_trace(current_span):
        nr_span = trace.get_current_span()
        assert current_span is not nr_span

    tracer = trace.get_tracer(__name__)

    foo_span = tracer.start_span("foo")
    with trace.use_span(foo_span, end_on_exit=True) as span1:
        assert foo_span == span1
        with tracer.start_as_current_span("bar") as span2:
            bar_span = trace.get_current_span()
            assert bar_span == span2
            assert bar_span.nr_trace.parent == foo_span.nr_trace
            baz_span = tracer.start_span("baz")
            with trace.use_span(baz_span, end_on_exit=True) as span3:
                assert baz_span == span3
                new_relic_function_trace(baz_span)


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
    * `add_custom_attribute` adds custom attributes to the transaction.
    * `add_custom_span_attribute` adds custom attributes to the trace.
    NOTE: a transaction's custom attributes are added to the root
    span's user attributes.
    """
    tracer = trace.get_tracer(__name__)

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
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("foo"):
            add_custom_span_attribute("OTel span", "Branched from NR")

    newrelic_background_task()
