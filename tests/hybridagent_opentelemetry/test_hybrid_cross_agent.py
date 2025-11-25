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

from opentelemetry import trace as otel_api_trace
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

tracer = otel_api_trace.get_tracer(__name__)


# Does not create segment without a transaction
@validate_transaction_count(0)
def test_does_not_create_segment_without_a_transaction():
    with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
        # The OpenTelmetry span should not be created
        assert otel_api_trace.get_current_span() == otel_api_trace.INVALID_SPAN

        # There should be no transaction
        assert not current_transaction()


# Creates OpenTelemetry segment in a transaction
@validate_transaction_metrics(name="Foo", background_task=True)
@validate_span_events(
    exact_intrinsics={"name": "Function/Bar", "category": "generic"}, expected_intrinsics=("parentId",)
)
@validate_span_events(exact_intrinsics={"name": "Function/Foo", "category": "generic", "nr.entryPoint": True})
def test_creates_opentelemetry_segment_in_a_transaction():
    application = application_instance(activate=False)

    with BackgroundTask(application, name="Foo"):
        with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
            # OpenTelemetry API and New Relic API report the same traceId
            assert otel_api_trace.get_current_span().get_span_context().trace_id == int(
                current_transaction()._trace_id, 16
            )

            # OpenTelemetry API and New Relic API report the same spanId
            assert otel_api_trace.get_current_span().get_span_context().span_id == int(current_trace().guid, 16)


# Creates New Relic span as child of OpenTelemetry span
@validate_transaction_metrics(name="Foo", background_task=True)
@validate_span_events(
    exact_intrinsics={"name": "Function/Baz", "category": "generic"}, expected_intrinsics=("parentId",)
)
@validate_span_events(
    exact_intrinsics={"name": "Function/Bar", "category": "generic"}, expected_intrinsics=("parentId",)
)
@validate_span_events(exact_intrinsics={"name": "Function/Foo", "category": "generic"})
def test_creates_new_relic_span_as_child_of_open_telemetry_span():
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
@validate_transaction_metrics(name="Foo", background_task=True)
@validate_span_events(exact_intrinsics={"name": "Function/Baz"}, exact_users={"spanNumber": 2})
@validate_span_events(exact_intrinsics={"name": "Function/Bar"}, exact_users={"spanNumber": 1})
def test_opentelemetry_api_can_add_custom_attributes_to_spans():
    application = application_instance(activate=False)

    with BackgroundTask(application, name="Foo"):
        with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
            with FunctionTrace(name="Baz"):
                otel_api_trace.get_current_span().set_attribute("spanNumber", 2)

            otel_api_trace.get_current_span().set_attribute("spanNumber", 1)


# OpenTelemetry API can record errors
@validate_transaction_metrics(name="Foo", background_task=True)
@validate_error_event_attributes(
    exact_attrs={"agent": {}, "intrinsic": {"error.message": "Test exception message"}, "user": {}}
)
@validate_span_events(exact_intrinsics={"name": "Function/Bar"})
def test_opentelemetry_api_can_record_errors():
    application = application_instance(activate=False)

    with BackgroundTask(application, name="Foo"):
        with tracer.start_as_current_span(name="Bar", kind=otel_api_trace.SpanKind.INTERNAL):
            try:
                raise Exception("Test exception message")
            except Exception as e:
                otel_api_trace.get_current_span().record_exception(e)
