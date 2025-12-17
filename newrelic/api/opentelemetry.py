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
from contextlib import contextmanager

from opentelemetry import trace as otel_api_trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.message_transaction import MessageTransaction
from newrelic.api.time_trace import current_trace, notice_error
from newrelic.api.transaction import Sentinel, current_transaction
from newrelic.api.web_transaction import WebTransaction
from newrelic.core.otlp_utils import create_resource

_logger = logging.getLogger(__name__)


class NRTraceContextPropagator(TraceContextTextMapPropagator):
    HEADER_KEYS = ("traceparent", "tracestate", "newrelic")

    def extract(self, carrier, context=None, getter=None):
        transaction = current_transaction()
        # If we are passing into New Relic, traceparent
        # and/or tracestate's keys also need to be NR compatible.

        if transaction:
            nr_headers = {
                header_key: getter.get(carrier, header_key)[0]
                for header_key in self.HEADER_KEYS
                if getter.get(carrier, header_key)
            }
            transaction.accept_distributed_trace_headers(nr_headers)
        return super().extract(carrier=carrier, context=context, getter=getter)

    def inject(self, carrier, context=None, setter=None):
        transaction = current_transaction()
        # Only insert headers if we have not done so already this transaction
        # New Relic's Distributed Trace State will have the following states:
        #   0 (00) if not set:
        #       Transaction has not inserted any outbound headers nor has
        #       it accepted any inbound headers (yet).
        #   1 (01) if already accepted:
        #       Transaction has accepted inbound headers and is able to
        #       insert outbound headers to the next app if needed.
        #   2 (10) if inserted but not accepted:
        #       Transaction has inserted outbound headers already.
        #       Do not insert outbound headers multiple times. This is
        #       a fundamental difference in OTel vs NR behavior: if
        #       headers are inserted by OTel multiple times, it will
        #       propagate the last set of data that was inserted. NR
        #       will not allow more than one header insertion per
        #       transaction.
        #   3 (11) if accepted, then inserted:
        #       Transaction has accepted inbound headers and has inserted
        #       outbound headers.

        if not transaction:
            return super().inject(carrier=carrier, context=context, setter=setter)

        if transaction._distributed_trace_state < 2:
            nr_headers = []
            transaction.insert_distributed_trace_headers(nr_headers)
            for key, value in nr_headers:
                setter.set(carrier, key, value)
            # Do NOT call super().inject() since we have already
            # inserted the headers here.  It will not cause harm,
            # but it is redundant logic.

        # If distributed_trace_state == 2 or 3, do not inject headers.


# Context and Context Propagator Setup
otel_context_propagator = CompositePropagator(propagators=[NRTraceContextPropagator(), W3CBaggagePropagator()])
set_global_textmap(otel_context_propagator)

# ----------------------------------------------
# Custom OTel Spans and Traces
# ----------------------------------------------


class Span(otel_api_trace.Span):
    def __init__(
        self,
        name=None,
        parent=None,  # SpanContext
        resource=None,
        attributes=None,
        kind=otel_api_trace.SpanKind.INTERNAL,
        nr_transaction=None,
        nr_trace_type=FunctionTrace,
        instrumenting_module=None,
        *args,
        **kwargs,
    ):
        self.name = name
        self.otel_parent = parent
        self.attributes = attributes or {}
        self.kind = kind
        self.nr_transaction = (
            nr_transaction or current_transaction()
        )  # This attribute is purely to prevent garbage collection
        self.nr_trace = None
        self.instrumenting_module = instrumenting_module

        self.nr_parent = None
        current_nr_trace = current_trace()
        if (
            not self.otel_parent
            or (self.otel_parent and self.otel_parent.span_id == int(current_nr_trace.guid, 16))
            or (self.otel_parent and isinstance(current_nr_trace, Sentinel))
        ):
            # Expected to come here if one of three scenarios have occured:
            # 1. `start_as_current_span` was used.
            # 2. `start_span` was used and the current span was explicitly set
            #    to the newly created one.
            # 3. Only a Sentinel Trace exists so far while still having a
            #    remote parent. From OTel's end, this will be represented
            #    as a `NonRecordingSpan` (and be seen as `None` at this
            #    point). This covers cases where span is remote.
            self.nr_parent = current_nr_trace
        else:
            # Not sure if there is a usecase where we could get in here
            # but for debug purposes, we will log this with details
            _logger.error(
                "OpenTelemetry span (%s) and NR trace (%s) do not match nor correspond to a remote span. Open Telemetry span will not be reported to New Relic. Please report this problem to New Relic.",
                self.otel_parent,
                current_nr_trace,  # NR parent trace
            )
            return

        if nr_trace_type == FunctionTrace:
            trace_kwargs = {"name": self.name, "params": self.attributes, "parent": self.nr_parent}
            self.nr_trace = nr_trace_type(**trace_kwargs)
        elif nr_trace_type == DatastoreTrace:
            trace_kwargs = {
                "product": self.instrumenting_module,
                "target": None,
                "operation": self.name,
                "parent": self.nr_parent,
            }
            self.nr_trace = nr_trace_type(**trace_kwargs)
        elif nr_trace_type == ExternalTrace:
            trace_kwargs = {
                "library": self.name or self.instrumenting_module,
                "url": self.attributes.get("http.url"),
                "method": self.attributes.get("http.method"),
                "parent": self.nr_parent,
            }
            self.nr_trace = nr_trace_type(**trace_kwargs)
        elif nr_trace_type == MessageTrace:
            trace_kwargs = {
                "library": self.instrumenting_module,
                "operation": "Produce",
                "destination_type": "Topic",
                "destination_name": self.name,
                "params": self.attributes,
                "parent": self.nr_parent,
                "terminal": False,
            }
            self.nr_trace = nr_trace_type(**trace_kwargs)
        else:
            trace_kwargs = {"name": self.name, "params": self.attributes, "parent": self.nr_parent}
            self.nr_trace = nr_trace_type(**trace_kwargs)

        self.nr_trace.__enter__()

    def _remote(self):
        # Remote span denotes if propagated from a remote parent
        return bool(self.otel_parent and self.otel_parent.is_remote)

    def get_span_context(self):
        if not getattr(self, "nr_trace", False):
            return otel_api_trace.INVALID_SPAN_CONTEXT

        return otel_api_trace.SpanContext(
            trace_id=int(self.nr_transaction.trace_id, 16),
            span_id=int(self.nr_trace.guid, 16),
            is_remote=self._remote(),
            trace_flags=otel_api_trace.TraceFlags(0x01),
            trace_state=otel_api_trace.TraceState(),
        )

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def set_attributes(self, attributes):
        for key, value in attributes.items():
            self.set_attribute(key, value)

    def _set_attributes_in_nr(self, otel_attributes=None):
        if not (otel_attributes and hasattr(self, "nr_trace") and self.nr_trace):
            return
        for key, value in otel_attributes.items():
            self.nr_trace.add_custom_attribute(key, value)

    def add_event(self, name, attributes=None, timestamp=None):
        # TODO: Not implemented yet.
        raise NotImplementedError("Events are not implemented yet.")

    def add_link(self, context=None, attributes=None):
        # TODO: Not implemented yet.
        raise NotImplementedError("Not implemented yet.")

    def update_name(self, name):
        # Sentinel, MessageTrace, DatastoreTrace, and ExternalTrace
        # types do not have a name attribute
        self._name = name
        if hasattr(self, "nr_trace") and hasattr(self.nr_trace, "name"):
            self.nr_trace.name = self._name

    def is_recording(self):
        # If the trace has an end time set then it is done recording. Otherwise,
        # if it does not have an end time set and the transaction's priority
        # has not been set yet or it is set to something other than 0 then it
        # is also still recording.
        if getattr(self.nr_trace, "end_time", None):
            return False

        return getattr(self.nr_transaction, "priority", 1) > 0

    def set_status(self, status, description=None):
        # TODO: not implemented yet
        raise NotImplementedError("Not implemented yet")

    def record_exception(self, exception, attributes=None, timestamp=None, escaped=False):
        error_args = sys.exc_info() if not exception else (type(exception), exception, exception.__traceback__)

        if not hasattr(self, "nr_trace"):
            notice_error(error_args, attributes=attributes)
        else:
            self.nr_trace.notice_error(error_args, attributes=attributes)

    def end(self, end_time=None, *args, **kwargs):
        # We will ignore the end_time parameter and use NR's end_time

        # Check to see if New Relic trace ever existed or,
        # if it does, that trace has already ended
        nr_trace = hasattr(self, "nr_trace")
        if not nr_trace or (nr_trace and getattr(nr_trace, "end_time", None)):
            return

        # Add attributes as Trace parameters
        self._set_attributes_in_nr(self.attributes)

        # For each kind of NR Trace, we will need to add
        # specific attributes since they were likely not
        # available at the time of the trace's creation.
        if self.instrumenting_module in ("Redis", "Mongodb"):
            self.nr_trace.host = self.attributes.get("net.peer.name", self.attributes.get("server.address"))
            self.nr_trace.port_path_or_id = self.attributes.get("net.peer.port", self.attributes.get("server.port"))
            self.nr_trace.database_name = self.attributes.get("db.name")
            self.nr_trace.product = self.attributes.get("db.system")
        elif self.instrumenting_module == "Dynamodb":
            self.nr_trace.database_name = self.attributes.get("db.name")
            self.nr_trace.product = self.attributes.get("db.system")
            self.nr_trace.port_path_or_id = self.attributes.get("net.peer.port")
            self.nr_trace.host = self.attributes.get("dynamodb.{region}.amazonaws.com")

        # Set SpanKind attribute
        self._set_attributes_in_nr({"span.kind": self.kind})

        self.nr_trace.__exit__(*sys.exc_info())


class Tracer(otel_api_trace.Tracer):
    def __init__(self, resource=None, instrumentation_library=None, *args, **kwargs):
        self.resource = resource
        self.instrumentation_library = instrumentation_library.split(".")[-1].capitalize()

    def start_span(
        self,
        name,
        context=None,  # Optional[Context]
        kind=otel_api_trace.SpanKind.INTERNAL,
        attributes=None,
        links=None,
        start_time=None,
        record_exception=True,
        set_status_on_exception=True,
        *args,
        **kwargs,
    ):
        nr_trace_type = FunctionTrace
        transaction = current_transaction()
        self.nr_application = application_instance()
        self.attributes = attributes or {}

        if not self.nr_application.active:
            # Force application registration if not already active
            self.nr_application.activate()

        if not self.nr_application.settings.otel_bridge.enabled:
            return otel_api_trace.INVALID_SPAN

        # Retrieve parent span
        parent_span_context = otel_api_trace.get_current_span(context).get_span_context()

        if parent_span_context is None or not parent_span_context.is_valid:
            parent_span_context = None

        parent_span_trace_id = None
        if parent_span_context and self.nr_application.settings.distributed_tracing.enabled:
            parent_span_trace_id = parent_span_context.trace_id

        # If remote_parent, transaction must be created, regardless of kind type
        # Make sure we transfer DT headers when we are here, if DT is enabled
        if parent_span_context and parent_span_context.is_remote:
            if kind in (otel_api_trace.SpanKind.SERVER, otel_api_trace.SpanKind.CLIENT):
                # This is a web request
                headers = self.attributes.pop("nr.http.headers", None)
                scheme = self.attributes.get("http.scheme")
                host = self.attributes.get("http.server_name")
                port = self.attributes.get("net.host.port")
                request_method = self.attributes.get("http.method")
                request_path = self.attributes.get("http.route")

                transaction = WebTransaction(
                    self.nr_application,
                    name=name,
                    scheme=scheme,
                    host=host,
                    port=port,
                    request_method=request_method,
                    request_path=request_path,
                    headers=headers,
                )

            elif kind in (otel_api_trace.SpanKind.PRODUCER, otel_api_trace.SpanKind.INTERNAL):
                transaction = BackgroundTask(self.nr_application, name=name)
            elif kind == otel_api_trace.SpanKind.CONSUMER:
                transaction = MessageTransaction(
                    library=self.instrumentation_library,
                    destination_type="Topic",
                    destination_name=name,
                    application=self.nr_application,
                    transport_type=self.instrumentation_library,
                    headers=None,
                )

            transaction.__enter__()

        # If not parent_span_context or not parent_span_context.is_remote
        # To simplify calculation logic, we will use DeMorgan's Theorem:
        # (!parent_span_context or !parent_span_context.is_remote)
        # !!(!parent_span_context or !parent_span_context.is_remote)
        # !(parent_span_context and parent_span_context.is_remote)
        elif not (parent_span_context and parent_span_context.is_remote):
            if kind == otel_api_trace.SpanKind.SERVER:
                if transaction:
                    nr_trace_type = FunctionTrace
                elif not transaction:
                    # This is a web request
                    headers = self.attributes.pop("nr.http.headers", None)
                    scheme = self.attributes.get("http.scheme")
                    host = self.attributes.get("http.server_name")
                    port = self.attributes.get("net.host.port")
                    request_method = self.attributes.get("http.method")
                    request_path = self.attributes.get("http.route")

                    transaction = WebTransaction(
                        self.nr_application,
                        name=name,
                        scheme=scheme,
                        host=host,
                        port=port,
                        request_method=request_method,
                        request_path=request_path,
                        headers=headers,
                    )

                    transaction._trace_id = (
                        f"{parent_span_trace_id:x}" if parent_span_trace_id else transaction.trace_id
                    )

                transaction.__enter__()
            elif kind == otel_api_trace.SpanKind.INTERNAL:
                if transaction:
                    nr_trace_type = FunctionTrace
                else:
                    return otel_api_trace.INVALID_SPAN
            elif kind == otel_api_trace.SpanKind.CLIENT:
                if transaction:
                    if self.attributes.get("http.url") or self.attributes.get("http.method"):
                        nr_trace_type = ExternalTrace
                    else:
                        nr_trace_type = DatastoreTrace
                else:
                    return otel_api_trace.INVALID_SPAN
            elif kind == otel_api_trace.SpanKind.CONSUMER:
                if transaction:
                    nr_trace_type = FunctionTrace
                elif not transaction:
                    transaction = MessageTransaction(
                        library=self.instrumentation_library,
                        destination_type="Topic",
                        destination_name=name,
                        application=self.nr_application,
                        transport_type=self.instrumentation_library,
                        headers=None,
                    )
                    transaction.__enter__()
            elif kind == otel_api_trace.SpanKind.PRODUCER:
                if transaction:
                    nr_trace_type = MessageTrace
                else:
                    return otel_api_trace.INVALID_SPAN

        # Start transactions in this method, but start traces
        # in Span.  Span function will take in some Span args
        # as well as info for NR applications/transactions
        span = Span(
            name=name,
            parent=parent_span_context,
            resource=self.resource,
            attributes=attributes,
            kind=kind,
            nr_transaction=transaction,
            nr_trace_type=nr_trace_type,
            instrumenting_module=self.instrumentation_library,
        )

        return span

    @contextmanager
    def start_as_current_span(
        self,
        name=None,
        context=None,
        kind=otel_api_trace.SpanKind.INTERNAL,
        attributes=None,
        links=None,
        end_on_exit=True,
        record_exception=True,
        set_status_on_exception=True,
    ):
        span = self.start_span(
            name,
            context=context,
            kind=kind,
            attributes=attributes,
            record_exception=record_exception,
            set_status_on_exception=set_status_on_exception,
        )

        with otel_api_trace.use_span(span, end_on_exit=end_on_exit, record_exception=record_exception) as current_span:
            yield current_span


class TracerProvider(otel_api_trace.TracerProvider):
    def __init__(self, *args, **kwargs):
        self._resource = create_resource(hybrid_bridge=True)

    def get_tracer(
        self,
        instrumenting_module_name="Default",
        instrumenting_library_version=None,
        schema_url=None,
        attributes=None,
        *args,
        **kwargs,
    ):
        return Tracer(*args, resource=self._resource, instrumentation_library=instrumenting_module_name, **kwargs)
