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

# Attributes that help distinguish span types are
# sometimes added after span creation and sometimes
# they are added during span creation.  During the case
# of the former, we have no way of knowing what sort of
# library instrumentation to apply, so we have a
# dictionary of module types as a safeguard.
#
# Transactions:
#   "web": Web Application
#   "wsgi": WSGI Web Application
#   "asgi": ASGI Web Application
#   "other": Background Task
#   "message": Message Queue
# Traces:
#   "other": Function Trace
#   "db": Database/Datastore
#   "message": Message Queue
#
INSTRUMENTING_MODULE_TYPE = {
    "Redis": "db",
    "Mongodb": "db",
    "Dynamodb": "db",
    "Pika": "message",
    "Kombu": "message",
    "Kafka": "message",
    "Flask": "wsgi",
    "Requests": "external",
}
# ----------------------------------------------
# Custom OTel Spans and Traces
# ----------------------------------------------

# TracerProvider: we can think of this as the agent instance.  Only one can exist
# SpanProcessor: we can think of this as an application.  In NR, we can have multiple applications
#   though right now, we can only do SpanProcessor and SynchronousMultiSpanProcessor
# Tracer: we can think of this as the transaction.
# Span: we can think of this as the trace.
# Links functionality has now been enabled but not implemented yet.  Links are relationships
#   between spans, but lateral in hierarchy.  In NR we only have parent-child relationships.
#   We may want to preserve this information with a custom attribute.  We can also add this
#   as a new attribute in a trace, but it will still not be seen in the UI other than a trace
#   attribute.


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

        # Do not create a New Relic trace if parent
        # is a remote span and it is not sampled
        if self._is_remote() and not self._is_sampled():
            return

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
            # but for debug purposes, we will raise an error
            _logger.warning(
                "OpenTelemetry span (%s) and NR trace (%s) do not match nor correspond to a remote span.",
                self.otel_parent,
                current_nr_trace,
            )
            raise ValueError("Unexpected span parent scenario encountered")

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
            # TODO: Still need to implement GraphQLOperationTrace and GraphQLResolverTrace
            trace_kwargs = {"name": self.name, "params": self.attributes, "parent": self.nr_parent}
            self.nr_trace = nr_trace_type(**trace_kwargs)

        self.nr_trace.__enter__()

    def _is_sampled(self):
        # Uses NR to determine if the trace is sampled

        # transaction.sampled can be None, True, False.
        # If None, this has not been computed by NR which
        # can also mean the following:
        # 1. There was not a context passed in that explicitly has sampling disabled.
        #   This flag would be found in the traceparent or traceparent and tracespan headers.
        # 2. Transaction was not created where DT headers are accepted during __init__
        # Therefore, we will treat a value of `None` as `True` for now.

        if self.otel_parent:
            return bool(self.otel_parent.trace_flags)
        else:
            return bool(self.nr_transaction and (self.nr_transaction.sampled or (self.nr_transaction.sampled is None)))

    def _is_remote(self):
        # Remote span denotes if propagated from a remote parent
        return bool(self.otel_parent and self.otel_parent.is_remote)

    def get_span_context(self):
        if not getattr(self, "nr_trace", False):
            return otel_api_trace.INVALID_SPAN_CONTEXT

        otel_tracestate_headers = None

        return otel_api_trace.SpanContext(
            trace_id=int(self.nr_transaction.trace_id, 16),
            span_id=int(self.nr_trace.guid, 16),
            is_remote=self._is_remote(),
            trace_flags=otel_api_trace.TraceFlags(0x01 if self._is_sampled() else 0x00),
            trace_state=otel_api_trace.TraceState(otel_tracestate_headers),
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
        # We can implement this as a log event
        pass

    def add_link(self, context=None, attributes=None):
        # TODO: Not implemented yet.
        pass

    def update_name(self, name):
        # Sentinel, MessageTrace, DatastoreTrace, and ExternalTrace
        # types do not have a name attribute
        self._name = name
        if hasattr(self, "nr_trace") and hasattr(self.nr_trace, "name"):
            self.nr_trace.name = self._name

    def is_recording(self):
        return self._is_sampled() and not (
            hasattr(self, "nr_trace") and hasattr(self.nr_trace, "end_time") and self.nr_trace.end_time
        )

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
        nr_trace = hasattr(self, "nr_trace", None)
        if not nr_trace or nr_trace and getattr(nr_trace, "end_time", None):
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
        # Retrieve parent span
        parent_span_context = otel_api_trace.get_current_span(context).get_span_context()

        if parent_span_context is None or not parent_span_context.is_valid:
            parent_span_context = None

        nr_trace_type = FunctionTrace
        transaction = current_transaction()
        self.nr_application = application_instance()
        self.attributes = attributes or {}

        # If remote_parent, transaction must be created, regardless of kind type
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
                # NOTE: NR uses MessageTransaction for Pika, RabbitMQ, Kafka
                if (
                    self.instrumentation_library in INSTRUMENTING_MODULE_TYPE
                    and INSTRUMENTING_MODULE_TYPE[self.instrumentation_library] == "message"
                ):
                    transaction = MessageTransaction(
                        library=self.instrumentation_library,
                        destination_type="Topic",
                        destination_name=name,
                        application=self.nr_application,
                        transport_type=self.instrumentation_library,
                        headers=headers,
                    )
                else:
                    transaction = BackgroundTask(self.nr_application, name=name, group="Celery")

            transaction.__enter__()

        # If not parent_span_context or not parent_span_context.is_remote
        # To simplify calculation logic, we will use Demorgan's Theorem:
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
                transaction.__enter__()
            elif kind == otel_api_trace.SpanKind.INTERNAL:
                if transaction:
                    nr_trace_type = FunctionTrace
                else:
                    return otel_api_trace.INVALID_SPAN
            elif kind == otel_api_trace.SpanKind.CLIENT:
                if transaction:
                    if (
                        (self.instrumentation_library in INSTRUMENTING_MODULE_TYPE)
                        and (INSTRUMENTING_MODULE_TYPE[self.instrumentation_library] == "db")
                    ) or (attributes and ("db.system" in attributes)):
                        nr_trace_type = DatastoreTrace
                    else:
                        nr_trace_type = ExternalTrace
                else:
                    return otel_api_trace.INVALID_SPAN
            elif kind == otel_api_trace.SpanKind.CONSUMER:
                if transaction:
                    nr_trace_type = FunctionTrace
                elif not transaction:
                    # NOTE: NR uses MessageTransaction for Pika, RabbitMQ, Kafka
                    if (
                        self.instrumentation_library in INSTRUMENTING_MODULE_TYPE
                        and INSTRUMENTING_MODULE_TYPE[self.instrumentation_library] == "message"
                    ):
                        transaction = MessageTransaction(
                            library=self.instrumentation_library,
                            destination_type="Topic",
                            destination_name=name,
                            application=self.nr_application,
                            transport_type=self.instrumentation_library,
                            headers=headers,
                        )
                    else:
                        transaction = BackgroundTask(self.nr_application, name=name, group="Celery")
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
        return Tracer(resource=self._resource, instrumentation_library=instrumenting_module_name)
