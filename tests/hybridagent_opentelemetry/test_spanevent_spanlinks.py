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
from opentelemetry.trace import Link, SpanContext, TraceState
from testing_support.fixtures import dt_enabled
from testing_support.validators.validate_spanlink_spanevent_events import validate_spanlink_or_spanevent_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@dt_enabled
@validate_spanlink_or_spanevent_events(
    exact_intrinsics={"name": "otelevent2", "type": "SpanEvent"},
    expected_intrinsics=["timestamp", "span.id", "trace.id", "name"],
    exact_users={"key99": "value99", "universe": 42},
)
@validate_spanlink_or_spanevent_events(
    exact_intrinsics={"name": "otelevent1", "type": "SpanEvent"},
    expected_intrinsics=["timestamp", "span.id", "trace.id", "name"],
    exact_users={"key1": "value1", "key2": 42},
)
def test_spanevent_events(tracer):
    @background_task()
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            otel_span.add_event("otelevent1", attributes={"key1": "value1", "key2": 42})
            otel_span.add_event("otelevent2", attributes={"key99": "value99", "universe": 42})

    _test()


@dt_enabled
@validate_spanlink_or_spanevent_events(count=0)
def test_spanevent_events_missing_name(tracer):
    @background_task()
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            otel_span.add_event(name=None, attributes={"key1": "value1", "key2": 42})

    _test()


@dt_enabled
@validate_spanlink_or_spanevent_events(
    exact_intrinsics={
        "type": "SpanLink",
        "linkedSpanId": "1234567890abcdef",
        "linkedTraceId": "1234567890abcdef1234567890abcdef",
    },
    expected_intrinsics=["timestamp", "id", "trace.id", "linkedSpanId", "linkedTraceId"],
    exact_users={"key1": "value1", "key2": 42},
)
def test_spanlink_events_upon_creation(tracer):
    linked_span_context = SpanContext(
        trace_id=0x1234567890ABCDEF1234567890ABCDEF,
        span_id=0x1234567890ABCDEF,
        is_remote=True,
        trace_flags=0x01,
        trace_state=TraceState(),
    )

    @background_task()
    def _test():
        with tracer.start_as_current_span(
            "otelspan", links=[Link(linked_span_context, attributes={"key1": "value1", "key2": 42})]
        ):
            pass

    _test()


@dt_enabled
@validate_spanlink_or_spanevent_events(
    exact_intrinsics={
        "type": "SpanLink",
        "linkedSpanId": "1234567890abcdef",
        "linkedTraceId": "1234567890abcdef1234567890abcdef",
    },
    expected_intrinsics=["timestamp", "id", "trace.id", "linkedSpanId", "linkedTraceId"],
    exact_users={"key1": "value1", "key2": 42},
)
def test_spanlink_events_within_span(tracer):
    linked_span_context = SpanContext(
        trace_id=0x1234567890ABCDEF1234567890ABCDEF,
        span_id=0x1234567890ABCDEF,
        is_remote=True,
        trace_flags=0x01,
        trace_state=TraceState(),
    )

    @background_task()
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            otel_span.add_link(linked_span_context, attributes={"key1": "value1", "key2": 42})

    _test()


@pytest.mark.parametrize(
    "trace_id,span_id,span_context",
    [(0, 0, True), (0x1234567890ABCDEF1234567890ABCDEF, 0, True), (0, 0x1234567890ABCDEF, True), (0, 0, False)],
)
@dt_enabled
@validate_spanlink_or_spanevent_events(count=0)
def test_spanlink_events_with_invalid_span_context(tracer, trace_id, span_id, span_context):
    linked_span_context = SpanContext(
        trace_id=trace_id, span_id=span_id, is_remote=True, trace_flags=0x01, trace_state=TraceState()
    )

    @background_task()
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            if span_context:
                otel_span.add_link(linked_span_context, attributes={"key1": "value1", "key2": 42})
            else:
                otel_span.add_link(None, attributes={"key1": "value1", "key2": 42})

    _test()


@dt_enabled
@validate_spanlink_or_spanevent_events(
    exact_intrinsics={"type": "SpanEvent", "name": "otelevent"},
    expected_intrinsics=["timestamp", "span.id", "trace.id", "name"],
    exact_users={"key99": "value99", "universe": 42},
)
@validate_spanlink_or_spanevent_events(
    exact_intrinsics={
        "type": "SpanLink",
        "linkedSpanId": "1234567890abcdef",
        "linkedTraceId": "1234567890abcdef1234567890abcdef",
    },
    expected_intrinsics=["timestamp", "id", "trace.id", "linkedSpanId", "linkedTraceId"],
    exact_users={"key1": "value1", "key2": 42},
)
def test_spanlink_and_spanevent_events(tracer):
    linked_span_context = SpanContext(
        trace_id=0x1234567890ABCDEF1234567890ABCDEF,
        span_id=0x1234567890ABCDEF,
        is_remote=True,
        trace_flags=0x01,
        trace_state=TraceState(),
    )

    @background_task()
    def _test():
        with tracer.start_as_current_span(
            "otelspan", links=[Link(linked_span_context, attributes={"key1": "value1", "key2": 42})]
        ) as otel_span:
            otel_span.add_event("otelevent", attributes={"key99": "value99", "universe": 42})

    _test()


@dt_enabled
@validate_spanlink_or_spanevent_events(
    count=100,
    exact_intrinsics={"name": "otelevent", "type": "SpanEvent"},
    expected_intrinsics=["timestamp", "span.id", "trace.id", "name"],
    exact_users={"key1": "value1", "key2": 42},
)
@validate_transaction_metrics(
    "test_spanevent_spanlinks:test_spanevent_events_over_limit.<locals>._test",
    rollup_metrics=[
        ("Supportability/SpanEvent/Events/Dropped", 3),
    ],
    background_task=True,
)
def test_spanevent_events_over_limit(tracer):
    @background_task()
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            for _ in range(103):
                otel_span.add_event("otelevent", attributes={"key1": "value1", "key2": 42})

    _test()


@dt_enabled
@validate_spanlink_or_spanevent_events(
    count=100,
    exact_intrinsics={
        "type": "SpanLink",
    },
    expected_intrinsics=["timestamp", "id", "trace.id", "linkedSpanId", "linkedTraceId"],
    exact_users={"key1": "value1", "key2": 42},
)
@validate_transaction_metrics(
    "test_spanevent_spanlinks:test_spanlink_events_over_limit.<locals>._test",
    rollup_metrics=[
        ("Supportability/SpanEvent/Links/Dropped", 3),
    ],
    background_task=True,
)
def test_spanlink_events_over_limit(tracer):  
    @background_task()
    def _test():
        with tracer.start_as_current_span("otelspan") as otel_span:
            for incrementer in range(103):
                linked_span_context = SpanContext(
                    trace_id=0x1234567890ABCDEF1234567890ABCDEF + incrementer,
                    span_id=0x1234567890ABCDEF + incrementer,
                    is_remote=True,
                    trace_flags=0x01,
                    trace_state=TraceState(),
                )  
                otel_span.add_link(linked_span_context, attributes={"key1": "value1", "key2": 42})

    _test()
