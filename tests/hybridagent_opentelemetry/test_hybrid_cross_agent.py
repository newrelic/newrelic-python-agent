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

from opentelemetry import propagate as otel_api_propagate
from opentelemetry import trace as otel_api_trace
from testing_support.fixtures import dt_enabled, override_application_settings
from testing_support.validators.validate_error_event_attributes import validate_error_event_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_count import validate_transaction_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction

PROPAGATOR = otel_api_propagate.get_global_textmap()


# Does not create segment without a transaction
@validate_transaction_count(0)
def test_does_not_create_segment_without_a_transaction(tracer):
    with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
        # The OpenTelmetry span should not be created
        assert otel_api_trace.get_current_span() == otel_api_trace.INVALID_SPAN

        # There should be no transaction
        assert not current_transaction()


# Creates OpenTelemetry segment in a transaction
@dt_enabled
@validate_transaction_metrics(name="Foo", background_task=True)
@validate_span_events(
    exact_intrinsics={
        "name": "Function/Bar",
        "category": "generic",
    },
    expected_intrinsics=("parentId",)
)
@validate_span_events(
    exact_intrinsics={
          "name": "Function/Foo",
          "category": "generic",
          "nr.entryPoint": True
    },
)
@validate_span_events(exact_intrinsics={"name": "Function/Foo", "category": "generic", "nr.entryPoint": True})
@validate_span_events(exact_intrinsics={"name": "Function/Foo", "category": "generic", "nr.entryPoint": True})
@validate_span_events(exact_intrinsics={"name": "Function/Foo", "category": "generic", "nr.entryPoint": True})
def test_creates_opentelemetry_segment_in_a_transaction(tracer):
    application = application_instance(activate=False)

    with BackgroundTask(application, name="Foo"):
        with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
            # OpenTelemetry API and New Relic API report the same traceId
            assert otel_api_trace.get_current_span().get_span_context().trace_id == int(
                current_transaction().trace_id, 16
            )

            # OpenTelemetry API and New Relic API report the same spanId
            assert otel_api_trace.get_current_span().get_span_context().span_id == int(current_trace().guid, 16)


# Creates New Relic span as child of OpenTelemetry span
@dt_enabled
@validate_transaction_metrics(name="Foo", background_task=True)
@validate_span_events(
    exact_intrinsics={
        "name": "Function/Baz",
        "category": "generic",
    },
    expected_intrinsics=("parentId",)
)
@validate_span_events(
    exact_intrinsics={
        "name": "Function/Bar",
        "category": "generic",
    },
    expected_intrinsics=("parentId",)
)
@validate_span_events(exact_intrinsics={"name": "Function/Foo", "category": "generic", "nr.entryPoint": True})
@validate_span_events(exact_intrinsics={"name": "Function/Foo", "category": "generic"})
def test_creates_new_relic_span_as_child_of_open_telemetry_span(tracer):
    application = application_instance(activate=False)

    with BackgroundTask(application, name="Foo"):
        with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
            with FunctionTrace(name="Baz"):
                # OpenTelemetry API and New Relic API report the same traceId
                assert otel_api_trace.get_current_span().get_span_context().trace_id == int(
                    current_transaction().trace_id, 16
                )

                # OpenTelemetry API and New Relic API report the same spanId
                assert otel_api_trace.get_current_span().get_span_context().span_id == int(current_trace().guid, 16)


# OpenTelemetry API can add custom attributes to spans
@dt_enabled
@validate_transaction_metrics(name="Foo", background_task=True)
@validate_span_events(exact_intrinsics={"name": "Function/Baz"}, exact_users={"spanNumber": 2})
@validate_span_events(exact_intrinsics={"name": "Function/Bar"}, exact_users={"spanNumber": 1})
def test_opentelemetry_api_can_add_custom_attributes_to_spans(tracer):
    application = application_instance(activate=False)

    with BackgroundTask(application, name="Foo"):
        with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
            with FunctionTrace(name="Baz"):
                otel_api_trace.get_current_span().set_attribute("spanNumber", 2)

            otel_api_trace.get_current_span().set_attribute("spanNumber", 1)


# OpenTelemetry API can record errors
@dt_enabled
@validate_transaction_metrics(name="Foo", background_task=True)
@validate_error_event_attributes(
    exact_attrs={"agent": {}, "intrinsic": {"error.message": "Test exception message"}, "user": {}}
)
@validate_span_events(exact_intrinsics={"name": "Function/Bar"})
def test_opentelemetry_api_can_record_errors(tracer):
    application = application_instance(activate=False)

    with pytest.raises(Exception, match="Test exception message"):
        with BackgroundTask(application, name="Foo"):
            with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
                raise Exception("Test exception message")


# OpenTelemetry API and New Relic API can inject outbound trace context
@dt_enabled
@validate_transaction_metrics(name="Foo", background_task=True)
@validate_span_events(exact_intrinsics={"name": "External/url1/Default/GET"}, expected_intrinsics=("parentId",))
@validate_span_events(exact_intrinsics={"name": "External/url2/segment1/GET"}, expected_intrinsics=("parentId",))
@validate_span_events(exact_intrinsics={"name": "External/url3/Default/GET"}, expected_intrinsics=("parentId",))
@validate_span_events(exact_intrinsics={"name": "External/url4/segment2/GET"}, expected_intrinsics=("parentId",))
def test_opentelemetry_api_and_new_relic_api_can_inject_outbound_trace_context(tracer):
    application = application_instance(activate=False)

    with BackgroundTask(application, name="Foo"):
        transaction = current_transaction()
        with tracer.start_as_current_span(
            name="OtelSpan1",
            kind=otel_api_trace.SpanKind.CLIENT,
            attributes={"http.url": "http://url1", "http.method": "GET"},
        ) as span1:
            headers = {}
            PROPAGATOR.inject(carrier=headers)
            _, trace_id, span_id, sampled = headers["traceparent"].split("-")

            # Correct traceId was injected
            assert transaction.trace_id == trace_id

            # Correct spanId was injected
            assert current_trace().guid == span_id

            # Correct sampled flag was injected
            assert transaction.sampled == (sampled == "01")
            
            # Assert that the span name is correct even though
            # ExternalTrace types do not have a name attribute
            assert span1.name == "OtelSpan1"

        # Reset the distributed trace state for the purposes of this test
        transaction._distributed_trace_state = 0

        with ExternalTrace(library="segment1", url="http://url2", method="GET"):
            headers = {}
            PROPAGATOR.inject(carrier=headers)
            _, trace_id, span_id, sampled = headers["traceparent"].split("-")

            # Correct traceId was injected
            assert current_transaction().trace_id == trace_id

            # Correct spanId was injected
            assert current_trace().guid == span_id

            # Correct sampled flag was injected
            assert current_transaction().sampled == (sampled == "01")

        # Reset the distributed trace state for the purposes of this test
        transaction._distributed_trace_state = 0

        with tracer.start_as_current_span(
            name="OtelSpan2",
            kind=otel_api_trace.SpanKind.CLIENT,
            attributes={"http.url": "http://url3", "http.method": "GET"},
        ) as span2:
            headers = []
            transaction.insert_distributed_trace_headers(headers)
            _, trace_id, span_id, sampled = headers[0][1].split("-")

            # Correct traceId was injected
            assert transaction.trace_id == trace_id

            # Correct spanId was injected
            assert current_trace().guid == span_id

            # Correct sampled flag was injected
            assert transaction.sampled == (sampled == "01")

            # Assert that the span name is correct even though
            # ExternalTrace types do not have a name attribute
            assert span2.name == "OtelSpan2"

        # Reset the distributed trace state for the purposes of this test
        transaction._distributed_trace_state = 0

        with ExternalTrace(library="segment2", url="http://url4", method="GET"):
            headers = []
            transaction.insert_distributed_trace_headers(headers)
            _, trace_id, span_id, sampled = headers[0][1].split("-")

            # Correct traceId was injected
            assert current_transaction().trace_id == trace_id

            # Correct spanId was injected
            assert current_trace().guid == span_id

            # Correct sampled flag was injected
            assert current_transaction().sampled == (sampled == "01")


# Starting transaction tests
@dt_enabled
@validate_transaction_metrics(name="Foo", index=-3)
@validate_transaction_metrics(name="Bar", index=-2)
@validate_transaction_metrics(name="Baz", background_task=True, index=-1)
@validate_span_events(exact_intrinsics={"name": "Function/EdgeCase"}, expected_intrinsics=("parentId",))
@validate_span_events(exact_intrinsics={"name": "Function/Baz", "nr.entryPoint": True})
def test_starting_transaction_tests(tracer):
    application = application_instance(activate=False)

    with tracer.start_as_current_span(name="Foo", kind=otel_api_trace.SpanKind.SERVER):
        pass

    # Create remote span context and remote context
    remote_span_context = otel_api_trace.SpanContext(
        trace_id=0x1234567890ABCDEF1234567890ABCDEF,
        span_id=0x1234567890ABCDEF,
        is_remote=True,
        trace_flags=0x01,
        trace_state=otel_api_trace.TraceState(),
    )
    remote_context = otel_api_trace.set_span_in_context(otel_api_trace.NonRecordingSpan(remote_span_context))

    with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.SERVER, context=remote_context):
        pass

    with BackgroundTask(application, name="Baz"):
        with tracer.start_as_current_span(name="EdgeCase", kind=otel_api_trace.SpanKind.SERVER, context=remote_context):
            pass


# Inbound distributed tracing tests
@dt_enabled
@validate_transaction_metrics(name="Foo")
@validate_span_events(count=0)
@override_application_settings({"trusted_account_key": "1", "account_id": "1"})
def test_inbound_distributed_tracing_tests(tracer):
    """
    This test intends to check for a scenario where an external call
    span is made outside the context of an existing transaction.
    By flagging that span as not sampled in OTel, it means that the OTel
    api will reflect that our agent is also ignoring that span.  In
    this case, it will create the server transaction, but no spans.
    """
    with tracer.start_as_current_span(name="Foo", kind=otel_api_trace.SpanKind.SERVER):
        carrier = {
            "traceparent": "00-da8bc8cc6d062849b0efcf3c169afb5a-7d3efb1b173fecfa-00",
            "tracestate": "1@nr=0-0-1-12345678-7d3efb1b173fecfa-da8bc8cc6d062849-0-0.23456-1011121314151",
        }
        PROPAGATOR.extract(carrier=carrier)

        current_span = otel_api_trace.get_current_span()

        assert current_span.get_span_context().trace_id == 0xDA8BC8CC6D062849B0EFCF3C169AFB5A
