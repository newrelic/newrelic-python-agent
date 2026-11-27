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

import logging
import sys
from types import SimpleNamespace

import pytest
from opentelemetry import trace as otel_trace
from opentelemetry.trace import SpanContext, TraceFlags
from testing_support.fixtures import core_application_stats_engine, dt_enabled, override_application_settings
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from newrelic.api.time_trace import add_custom_span_attribute, current_trace
from newrelic.api.transaction import accept_distributed_trace_headers, current_transaction
from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper

ENTITY_GUID = "DEVELOPERMODEENTITYGUID"
ENTITY_URL = "https://fake-one.newrelic.com/redirect/DEVELOPERMODEENTITYGUID"
TRACE_ID = "0af7651916cd43dd8448eb211c80319c"
SPAN_ID = "b7ad6b7169203331"


@function_wrapper
def dt_unsampled(wrapped, instance, args, kwargs):
    """Counterpart to dt_enabled, forcing every transaction to be unsampled."""

    @transient_function_wrapper("newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled")
    def force_unsampled(wrapped, instance, args, kwargs):
        wrapped(*args, **kwargs)
        return False

    settings = {"distributed_tracing.enabled": True}
    wrapped = override_application_settings(settings)(wrapped)
    wrapped = force_unsampled(wrapped)

    return wrapped(*args, **kwargs)


@function_trace(name="child")
def child():
    return current_trace().guid


def exercise_transaction(tracer=None, headers=None, child_trace=child):
    """Run a transaction containing a root span, an NR child span and optionally an OTel span.

    Returns the trace and span ids of the NR spans.
    """

    @background_task(name="root")
    def _test():
        if headers:
            accept_distributed_trace_headers(headers)

        ids = {"trace_id": current_transaction().trace_id, "root": current_trace().guid, "child": child_trace()}
        if tracer:
            with tracer.start_as_current_span(name="otel-span"):
                pass
        return ids

    return _test()


def spans_by_guid(spans):
    return {format(span.context.span_id, "016x"): span for span in spans}


@dt_enabled
def test_forwards_each_nr_span_once(ld_spans):
    ids = exercise_transaction()

    spans = spans_by_guid(ld_spans.spans)
    assert len(ld_spans.spans) == 2
    assert set(spans) == {ids["root"], ids["child"]}
    for span in ld_spans.spans:
        assert format(span.context.trace_id, "032x") == ids["trace_id"].rjust(32, "0")
        assert span.name == span.attributes["name"]
        # Popped from the attributes into the span context.
        for name in ("traceId", "guid", "sampled"):
            assert name not in span.attributes

    assert spans[ids["child"]].name == "Function/child"
    assert spans[ids["root"]].attributes["nr.entryPoint"] is True


@dt_enabled
def test_timestamps_converted_to_ns(ld_spans):
    exercise_transaction()

    assert ld_spans.spans
    for span in ld_spans.spans:
        start_ns = int(span.attributes["timestamp"] * 10**6)
        assert span.start_time == start_ns
        assert span.end_time == int(span.attributes["timestamp"] * 10**6 + span.attributes["duration"] * 10**9)


@dt_enabled
def test_entity_attributes_on_every_span(ld_spans):
    exercise_transaction()

    assert len(ld_spans.spans) == 2
    for span in ld_spans.spans:
        assert span.attributes["nr.entity.guid"] == ENTITY_GUID
        assert span.attributes["nr.entity.url"] == ENTITY_URL


@dt_enabled
def test_otel_spans_not_forwarded(ld_spans, tracer):
    ids = exercise_transaction(tracer=tracer)

    assert set(spans_by_guid(ld_spans.spans)) == {ids["root"], ids["child"]}
    assert not any(span.name == "otel-span" for span in ld_spans.spans)


@dt_enabled
def test_sampled_spans_exported(ld_spans):
    exercise_transaction()

    assert len(ld_spans.spans) == 2
    assert all(span.context.trace_flags == TraceFlags(TraceFlags.SAMPLED) for span in ld_spans.spans)
    assert len(ld_spans.exporter.get_finished_spans()) == 2


@dt_unsampled
def test_unsampled_spans_not_exported(ld_spans):
    exercise_transaction()

    assert ld_spans.spans
    assert all(span.context.trace_flags == TraceFlags(TraceFlags.DEFAULT) for span in ld_spans.spans)
    assert not ld_spans.exporter.get_finished_spans()


@dt_enabled
def test_parent_span_applied(ld_spans):
    ids = exercise_transaction()

    spans = spans_by_guid(ld_spans.spans)
    root, child_span = spans[ids["root"]], spans[ids["child"]]

    # Root span without an inbound distributed trace has no parent.
    assert root.parent is None
    assert not root.context.is_remote

    assert child_span.parent is not None
    assert format(child_span.parent.span_id, "016x") == ids["root"]
    assert child_span.parent.trace_id == root.context.trace_id
    assert not child_span.parent.is_remote
    assert not child_span.context.is_remote
    assert child_span.attributes["parentId"] == ids["root"]


@dt_enabled
def test_remote_parent_span_applied(ld_spans):
    ids = exercise_transaction(headers={"traceparent": f"00-{TRACE_ID}-{SPAN_ID}-01"})

    assert ids["trace_id"] == TRACE_ID
    spans = spans_by_guid(ld_spans.spans)
    root, child_span = spans[ids["root"]], spans[ids["child"]]

    assert root.parent is not None
    assert format(root.parent.span_id, "016x") == SPAN_ID
    assert root.parent.is_remote
    assert not root.context.is_remote

    assert format(child_span.parent.span_id, "016x") == ids["root"]
    assert not child_span.parent.is_remote


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param({"launch_darkly_integration.enabled": False}, id="launch_darkly_disabled"),
        pytest.param({"opentelemetry.enabled": False}, id="opentelemetry_disabled"),
        pytest.param({"distributed_tracing.enabled": False}, id="dt_disabled"),
        pytest.param({"span_events.enabled": False}, id="span_events_disabled"),
        pytest.param({"collect_span_events": False}, id="collect_disabled"),
    ],
)
def test_forwarding_disabled(ld_spans, settings):
    @dt_enabled
    @override_application_settings(settings)
    def _test():
        exercise_transaction()

    _test()

    assert not ld_spans.spans


@dt_enabled
@override_application_settings({"infinite_tracing._trace_observer_host": "x"})
def test_forwarding_with_infinite_tracing(ld_spans, monkeypatch):
    stream_buffer_puts = []
    monkeypatch.setattr(core_application_stats_engine()._span_stream, "put", stream_buffer_puts.append, raising=False)

    exercise_transaction()

    assert len(ld_spans.spans) == 2
    assert len(stream_buffer_puts) == 2


@dt_enabled
def test_attribute_precedence(ld_spans):
    @function_trace(name="child")
    def _child():
        trace = current_trace()
        # "category" is an intrinsic, set to "generic" for function traces. Agent attributes must be
        # names allowed on span events by default, otherwise the attribute filter drops them.
        for name in ("category", "server.address", "user_only"):
            add_custom_span_attribute(name, "user")
        for name in ("category", "server.address", "server.port"):
            trace._add_agent_attribute(name, "agent")
        return trace.guid

    ids = exercise_transaction(child_trace=_child)

    span = spans_by_guid(ld_spans.spans)[ids["child"]]
    assert span.attributes["category"] == "generic"
    assert span.attributes["server.address"] == "agent"
    assert span.attributes["user_only"] == "user"
    assert span.attributes["server.port"] == "agent"


@pytest.mark.parametrize(
    "add_links,add_events",
    [
        pytest.param(False, False, id="plain"),
        pytest.param(True, False, id="links"),
        pytest.param(False, True, id="events"),
        pytest.param(True, True, id="links_and_events"),
    ],
)
@dt_enabled
def test_span_link_and_event_shapes(ld_spans, add_links, add_events):
    @function_trace(name="child")
    def _child():
        # Inside an NR trace, the OTel API returns a span backed by that trace, so links
        # and events are recorded on the NR span event.
        span = otel_trace.get_current_span()
        if add_links:
            span.add_link(SpanContext(trace_id=int(TRACE_ID, 16), span_id=int(SPAN_ID, 16), is_remote=True))
        if add_events:
            span.add_event("event")

        trace = current_trace()
        assert bool(trace.span_link_events) == add_links
        assert bool(trace.span_event_events) == add_events

        add_custom_span_attribute("user", "attr")
        trace._add_agent_attribute("server.address", "attr")
        return trace.guid

    ids = exercise_transaction(child_trace=_child)

    spans = spans_by_guid(ld_spans.spans)
    assert set(spans) == {ids["root"], ids["child"]}
    span = spans[ids["child"]]
    assert span.name == "Function/child"
    assert format(span.context.trace_id, "032x") == ids["trace_id"].rjust(32, "0")
    assert span.attributes["user"] == "attr"
    assert span.attributes["server.address"] == "attr"


@pytest.mark.parametrize(
    "unavailable",
    [
        pytest.param(lambda monkeypatch: monkeypatch.setitem(sys.modules, "ldobserve", None), id="not_installed"),
        pytest.param(
            lambda monkeypatch: monkeypatch.setattr(sys.modules["ldobserve.observe"], "_instance", None),
            id="not_registered",
        ),
    ],
)
def test_ldobserve_unavailable_warns_once(ld_spans, monkeypatch, caplog, unavailable):
    unavailable(monkeypatch)

    @dt_enabled
    @validate_span_events(count=2)
    def _test():
        exercise_transaction()

    with caplog.at_level(logging.WARNING, logger="newrelic"):
        _test()
        _test()

    warnings = [record for record in caplog.records if "LaunchDarkly" in record.getMessage()]
    assert len(warnings) == 1
    assert warnings[0].levelno == logging.WARNING
    assert not ld_spans.spans


def test_forwarding_error_does_not_break_recording(ld_spans, monkeypatch, caplog):
    import ldobserve.observe

    class BrokenTracer:
        def start_span(self, *args, **kwargs):
            raise RuntimeError("Broken tracer")

    monkeypatch.setattr(ldobserve.observe, "_instance", SimpleNamespace(_tracer=BrokenTracer()))

    # Span events are still recorded in New Relic despite the failure.
    @dt_enabled
    @validate_span_events(count=2)
    def _test():
        exercise_transaction()

    with caplog.at_level(logging.ERROR, logger="newrelic"):
        _test()

    assert any("Failed to forward span data to LaunchDarkly" in record.getMessage() for record in caplog.records)


@dt_enabled
def test_no_invalid_otel_attributes(ld_spans, caplog):
    with caplog.at_level(logging.WARNING, logger="opentelemetry"):
        exercise_transaction()

    assert len(ld_spans.spans) == 2
    assert not [record for record in caplog.records if "Invalid type" in record.getMessage()]
