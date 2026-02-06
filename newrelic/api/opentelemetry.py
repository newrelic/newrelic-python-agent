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

import json
import logging
import sys
import time
from contextlib import contextmanager

from opentelemetry import trace as otel_api_trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace.status import Status, StatusCode

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.message_transaction import MessageTransaction
from newrelic.api.time_trace import current_trace, notice_error
from newrelic.api.transaction import Sentinel, current_transaction
from newrelic.api.web_transaction import WebTransaction, WSGIWebTransaction
from newrelic.core.attribute import sanitize
from newrelic.core.database_utils import (
    generate_dynamodb_arn,
    get_database_operation_target_from_statement,
    _all_literals_re,
    _quotes_table,
)
from newrelic.core.otlp_utils import create_resource

_logger = logging.getLogger(__name__)


def retry_application_activation(application, retries=10):
    count = 0
    while (not application.active) and count < retries:
        # Force application registration if not already active
        activation_wait = 0.5 + count*0.5
        application.activate()
        _logger.debug(f"Attempt #{count+1} to active application.  Waiting for {activation_wait} seconds.")
        time.sleep(activation_wait)
        count += 1
        
    if not application.active:
        raise RuntimeError("Failed to activate application after retries")


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

        extracted_context = super().extract(
            carrier=carrier, context=context, getter=getter
        )

        return extracted_context

    def inject(self, carrier, context=None, setter=None):
        transaction = current_transaction()
        if not transaction:
            return super().inject(carrier=carrier, context=context, setter=setter)

        nr_headers = []
        transaction.insert_distributed_trace_headers(nr_headers)
        for key, value in nr_headers:
            setter.set(carrier, key, value)
        # Do NOT call super().inject() since we have already
        # inserted the headers here.  It will not cause harm,
        # but it is redundant logic.


# Context and Context Propagator Setup
otel_context_propagator = CompositePropagator(
    propagators=[NRTraceContextPropagator(), W3CBaggagePropagator()]
)

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
        record_exception=True,
        set_status_on_exception=True,
        nr_transaction=None,
        nr_trace_type=FunctionTrace,
        instrumenting_module=None,
        create_nr_trace=True,
        links=None,
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
        self.status = Status(StatusCode.UNSET)
        self._record_exception = record_exception
        self.set_status_on_exception = set_status_on_exception
        self.links = links or []
        self.create_nr_trace = create_nr_trace

        self.nr_parent = None
        current_nr_trace = current_trace()
        if (
            not self.otel_parent
            or (
                self.otel_parent
                and self.otel_parent.span_id == int(current_nr_trace.guid, 16)
            )
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
            # This should not occur, but if it does, we need to
            # log an error and not create a New Relic trace.
            _logger.error(
                "OpenTelemetry span (%s) and NR trace (%s) do not match nor correspond to a remote span. Open Telemetry span will not be reported to New Relic. Please report this problem to New Relic.",
                self.otel_parent,
                current_nr_trace,  # NR parent trace
            )
            return

        if not self.create_nr_trace:
            # Do not create a New Relic trace for this OTel span.
            # While this OTel span exists it will not be explicitly
            # translated to a NR trace.  This may occur during the
            # creation of a Transaction, which will create the root
            # span.  This may also occur during special cases, such
            # as back to back calls to Kafka's queue's consumer.
            # If a transaction already exists, we do not want to
            # create another transaction or trace, but rather just
            # append existing attributes to the existing transaction.
            self.nr_trace = current_nr_trace
            # Add Instrumentation Scope Attributes
            self.nr_trace._add_agent_attribute("otel.scope.name", self.attributes.get("library_name"))
            self.nr_trace._add_agent_attribute("otel.scope.version", self.attributes.get("library_version"))
            self.nr_trace._add_agent_attribute("otel.library.name", self.attributes.get("library_name"))
            self.nr_trace._add_agent_attribute("otel.library.version", self.attributes.get("library_version"))
            return
        elif nr_trace_type == FunctionTrace:
            trace_kwargs = {
                "name": self.name,
                "params": self.attributes,
                "parent": self.nr_parent,
            }
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
                "library": self.instrumenting_module,
                "url": self.attributes.get("http.url"),
                "method": self.attributes.get("http.method") or self.name,
                "parent": self.nr_parent,
            }
            self.nr_trace = nr_trace_type(**trace_kwargs)
        elif nr_trace_type == MessageTrace:
            trace_kwargs = {
                "library": self.instrumenting_module,
                "operation": "Produce"
                if self.kind == otel_api_trace.SpanKind.PRODUCER
                else "Consume",
                "destination_type": "Exchange",  
                "destination_name": self.name,
                "params": self.attributes,
                "parent": self.nr_parent,
                "terminal": False,
            }
            self.nr_trace = nr_trace_type(**trace_kwargs)
        else:
            trace_kwargs = {
                "name": self.name,
                "params": self.attributes,
                "parent": self.nr_parent,
            }
            self.nr_trace = nr_trace_type(**trace_kwargs)

        self.nr_trace.__enter__()

        # Add Instrumentation Scope Attributes
        self.nr_trace._add_agent_attribute("otel.scope.name", self.attributes.get("library_name"))
        self.nr_trace._add_agent_attribute("otel.scope.version", self.attributes.get("library_version"))
        self.nr_trace._add_agent_attribute("otel.library.name", self.attributes.get("library_name"))
        self.nr_trace._add_agent_attribute("otel.library.version", self.attributes.get("library_version"))

        # Process Links that were passed in upon span creation
        for link in self.links:
            self.add_link(
                context=link.context,
                attributes=link.attributes,
                timestamp=self.nr_trace.start_time,
            )

    def _remote(self):
        """
        Remote span denotes if propagated from a remote parent
        """
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
        if not otel_attributes or not getattr(self, "nr_trace", None):
            return

        # If these attributes already exist in NR's agent attributes,
        # keep the attributes in the OTel span, but do not add them
        # to NR's user attributes to avoid sending the same data
        # multiple times.
        for key, value in otel_attributes.items():
            if key not in self.nr_trace.agent_attributes:
                self.nr_trace.add_custom_attribute(key, value)

    def add_event(self, name, attributes=None, timestamp=None):
        """Add an event to the current span.

        If timestamp is None, this will get set to the current time.
        """
        current_span_context = self.get_span_context()
        current_trace_id = f"{current_span_context.trace_id:032x}"
        current_span_id = f"{current_span_context.span_id:016x}"

        # Sanitize name, if not already a string.
        try:
            name = sanitize(name)
        except Exception as e:
            _logger.error(
                "Invalid event name %s passed to add_event; event will not be created. Error: %s",
                name,
                e,
            )
            return

        self.nr_trace._add_span_event_event(
            span_id=current_span_id,
            trace_id=current_trace_id,
            name=name,
            timestamp=timestamp,
            attributes=attributes,
        )

    def add_link(self, context=None, attributes=None, timestamp=None):
        """Add a link to another span.

        NOTE: `timestamp` is not an OTel specific value.  This is
        a Hybrid Agent specific argument that allows us to set the
        time of the link based on when the NR trace was created
        (if the link was passed in during the span's creation), or
        if added later on (the time when the link was added).
        """
        if not context or not context.is_valid:
            _logger.error(
                "Invalid span context passed to add_link; link will not be created."
            )
            return

        # If timestamp is None, use the current time
        if timestamp:
            timestamp = int(timestamp * 1e3)
        else:
            timestamp = int(time.time() * 1e3)

        link_trace_id = f"{context.trace_id:032x}"
        link_span_id = f"{context.span_id:016x}"
        current_span_context = self.get_span_context()
        current_trace_id = f"{current_span_context.trace_id:032x}"
        current_span_id = f"{current_span_context.span_id:016x}"

        self.nr_trace._add_span_link_event(
            span_id=current_span_id,
            trace_id=current_trace_id,
            linked_span_id=link_span_id,
            linked_trace_id=link_trace_id,
            timestamp=timestamp,
            attributes=attributes,
        )

    def update_name(self, name):
        # NOTE: Sentinel, MessageTrace, DatastoreTrace, and
        # ExternalTrace types do not have a name attribute.
        self.name = name
        if hasattr(self, "nr_trace") and hasattr(self.nr_trace, "name"):
            self.nr_trace.name = self.name

    def is_recording(self):
        # If the trace has an end time set then it is done recording. Otherwise,
        # if it does not have an end time set and the transaction's priority
        # has not been set yet or it is set to something other than 0 then it
        # is also still recording.
        if getattr(self.nr_trace, "end_time", None):
            return False

        # If priority is either not set at this point
        # or greater than 0, we are recording.
        priority = self.nr_transaction.priority
        return (priority is None) or (priority > 0)

    def set_status(self, status, description=None):
        """
        This code is modeled after the OpenTelemetry SDK's
        status implementation:
        https://github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py#L979

        Additional Notes:
        1. Ignore future calls if status is already set to OK
            since span should be completed if status is OK.
        2. Similarly, ignore calls to set to StatusCode.UNSET
            since this will be either invalid or unnecessary.
        """
        if isinstance(status, Status):
            if (self.status.status_code is StatusCode.OK) or status.is_unset:
                return
            if description is not None:
                # `description` should only exist if status is StatusCode.ERROR
                _logger.warning(
                    "Description %s ignored. Use either `Status` or `(StatusCode, Description)`",
                    description,
                )
            self.status = status
        elif isinstance(status, StatusCode):
            if (self.status.status_code is StatusCode.OK) or (
                status is StatusCode.UNSET
            ):
                return
            self.status = Status(status, description)
        else:
            _logger.warning(
                "Invalid status type %s. Expected Status or StatusCode.", type(status)
            )
            return

        # Add status as attribute
        self.set_attribute("status_code", self.status.status_code.name)
        self.set_attribute("status_description", self.status.description)

    def record_exception(
        self, exception, attributes=None, timestamp=None, escaped=False
    ):
        error_args = (
            sys.exc_info()
            if not exception
            else (type(exception), exception, exception.__traceback__)
        )

        # `escaped` indicates whether the exception has not
        # been unhandled by the time the span has ended.
        if attributes:
            attributes["exception.escaped"] = escaped
        else:
            attributes = {"exception.escaped": escaped}

        self.set_attributes(attributes)

        notice_error(error_args, attributes=attributes)

    def _obfuscate_query(self, sql, database):
        database_to_quote_style_mapping = {
            "postgresql": "single+dollar",
            "psycopg2": "single+dollar",
            "graphql": "single+double",
            "mysql": "single+double",
        }
        
        quotes_re, quotes_cleanup_re = _quotes_table.get(
            database_to_quote_style_mapping.get(database), _quotes_table.get("single")
        )
        sql = quotes_re.sub("?", sql)
        sql = _all_literals_re.sub("?", sql)
        if quotes_cleanup_re.search(sql):
            sql = "?"

        return sql

    def _messagequeue_attribute_mapping(self):
        host = self.attributes.get("net.peer.name") or self.attributes.get(
            "server.address"
        )
        port = self.attributes.get("net.peer.port") or self.attributes.get(
            "server.port"
        )
        name = self.name.split(maxsplit=1)[
            0
        ]  # OTel's format for this is "name operation"

        # Logic for Pika/RabbitMQ
        span_obj_attrs = {
            "library": self.attributes.get("messaging.system"),
            "destination_name": name,  # OTel's format for this is "name operation"
        }

        if span_obj_attrs["library"] == "rabbitmq":
            # In RabbitMQ, destination_type is always Exchange and
            # destination_name is actually stored in the span name.
            # messaging.destination stores the task_name (such as
            # consumer tag)
            span_obj_attrs["destination_type"] = "Exchange"

        agent_attrs = {
            "host": host,
            "port": port,
            "server.address": host,
            "server.port": port,
        }

        # Kafka Specific Logic
        if span_obj_attrs["library"] == "kafka":
            span_obj_attrs.update(
                {
                    "transport_type": "Kafka",
                    "destination_type": "Topic",
                    "destination_name": name
                    if (name != "unknown")
                    else "Default",  # OTel's format for this is "name operation"
                }
            )
            if isinstance(self.nr_transaction, MessageTransaction):
                self.nr_transaction.transport_type = "Kafka"
                self.nr_transaction.destination_type = "Topic"

                if (
                    self.nr_transaction.destination_name.startswith("unknown")
                    and span_obj_attrs["destination_name"] != "unknown"
                ):
                    self.nr_transaction.destination_name = span_obj_attrs[
                        "destination_name"
                    ]
                else:
                    self.nr_transaction.destination_name = "Default"

            bootstrap_servers = json.loads(self.attributes.get("messaging.url", "[]"))
            for server_name in bootstrap_servers:
                produce_or_consume = (
                    "Produce"
                    if self.kind == otel_api_trace.SpanKind.PRODUCER
                    else "Consume"
                )
                self.nr_transaction.record_custom_metric(
                    f"MessageBroker/kafka/Nodes/{server_name}/{produce_or_consume}/{span_obj_attrs['destination_name']}",
                    1,
                )

        # Even if the attribute is set to None, it should rename
        # the transaction destination_name attribute as well:
        if isinstance(self.nr_transaction, MessageTransaction):
            name, group = self.nr_transaction.get_transaction_name(
                span_obj_attrs["library"],
                span_obj_attrs["destination_type"],
                span_obj_attrs["destination_name"],
            )
            self.nr_transaction.set_transaction_name(name, group)

        # We do not want to override any agent attributes
        # with `None` if `value` does not exist.
        for key, value in span_obj_attrs.items():
            if value:
                setattr(self.nr_trace, key, value)
        for key, value in agent_attrs.items():
            if value:
                self.nr_trace._add_agent_attribute(key, value)

    def _database_attribute_mapping(self):
        span_obj_attrs = {
            "host": self.attributes.get("net.peer.name")
            or self.attributes.get("server.address"),
            "database_name": self.attributes.get("db.name"),
            "port_path_or_id": self.attributes.get("net.peer.port")
            or self.attributes.get("server.port"),
            "product": self.attributes.get("db.system", self.attributes.get("db.system.name")),
        }
        agent_attrs = {}

        db_statement = self.attributes.pop("db.statement", None)
        if db_statement:
            if hasattr(db_statement, "string"):
                db_statement = db_statement.string
            operation, target = get_database_operation_target_from_statement(
                db_statement
            )
            target = target or self.attributes.get("db.mongodb.collection")
            span_obj_attrs.update({"operation": operation, "target": target})
            if self.nr_transaction.application.settings.transaction_tracer.record_sql != "off":
                if self.nr_transaction.application.settings.transaction_tracer.record_sql == "obfuscated":
                    db_statement = self._obfuscate_query(db_statement, span_obj_attrs["product"])
                agent_attrs["db.statement"] = db_statement
        elif span_obj_attrs["product"] == "dynamodb":
            region = self.attributes.get("cloud.region")
            operation = self.attributes.get("db.operation", self.attributes.get("db.operation.name"))
            target = self.attributes.get("aws.dynamodb.table_names", [None])[-1]
            account_id = self.nr_transaction.settings.cloud.aws.account_id
            resource_id = generate_dynamodb_arn(
                span_obj_attrs["host"], region, account_id, target
            )
            agent_attrs.update(
                {
                    "aws.operation": operation,
                    "cloud.resource_id": resource_id,
                    "cloud.region": region,
                    "aws.requestId": self.attributes.get("aws.request_id"),
                    "http.statusCode": self.attributes.get("http.status_code"),
                    "cloud.account.id": account_id,
                }
            )
            span_obj_attrs.update({"target": target, "operation": operation})

        # We do not want to override any agent attributes
        # with `None` if `value` does not exist.
        for key, value in span_obj_attrs.items():
            if value:
                setattr(self.nr_trace, key, value)
        for key, value in agent_attrs.items():
            if value:
                self.nr_trace._add_agent_attribute(key, value)

    def _strawberry_operation_name_parser(self, span_name):
        if ": " in span_name:
            return span_name.split(": ")[1]
        return self.nr_trace.agent_attributes.get("graphql.operation.name")
    
    def _graphql_attribute_mapping(self):
        if self.nr_transaction.application.settings.transaction_tracer.record_sql == "obfuscated":
            sql_orig = self.attributes.get("query", "")
            sql = self._obfuscate_query(sql_orig, "graphql")
            
            if sql_orig:
                self.attributes["query"] = sql
            
            for key in self.attributes.keys():
                if ("graphql.arg" in key) or ("graphql.param." in key):
                    self.attributes[key] = "?"
        elif self.nr_transaction.application.settings.transaction_tracer.record_sql == "off":
            self.attributes.pop("query", None)
            for key in self.attributes.keys():
                if ("graphql.arg" in key) or ("graphql.param." in key):
                    self.attributes[key] = ""
        
        self.nr_trace._add_agent_attribute("graphql.field.path", self.attributes.get("graphql.path", self.nr_trace.agent_attributes.get("graphql.field.path")))
        self.nr_trace._add_agent_attribute("graphql.field.parentType", self.attributes.get("graphql.parentType", self.nr_trace.agent_attributes.get("graphql.field.parentType")))
        self.nr_trace._add_agent_attribute("graphql.operation.name", self.attributes.get("graphql.operation.name", self._strawberry_operation_name_parser(self.name)))
        self.nr_trace._add_agent_attribute("graphql.operation.query", self.attributes.get("query", self.nr_trace.agent_attributes.get("graphql.operation.query")))


    def end(self, end_time=None, *args, **kwargs):
        # We will ignore the end_time parameter and use NR's end_time

        # Check to see if New Relic trace ever existed
        # or, if it does, that trace has already ended
        if not self.nr_trace or getattr(self.nr_trace, "end_time", None):
            return

        # We will need to add specific attributes to the
        # NR trace before the node creation because the
        # attributes were likely not available at the time
        # of the trace's creation but eventually populated
        # throughout the span's lifetime.

        # Database/Datastore specific attributes
        if self.attributes.get("db.system", self.attributes.get("db.system.name")):
            self._database_attribute_mapping()

        # Message specific attributes
        if self.attributes.get("messaging.system"):
            self._messagequeue_attribute_mapping()

        # External/Web specific attributes
        if ("http.status_code" in self.attributes) and (isinstance(self.nr_transaction, WebTransaction)):
            response_headers = {key.split("http.response.header.")[1].replace("_", "-"): value[0] for key, value in self.attributes.items() if key.startswith("http.response.header.")}
            self.nr_transaction.process_response(str(self.attributes.get("http.status_code")), response_headers)
        
        self.nr_trace._add_agent_attribute(
            "http.statusCode", self.attributes.get("http.status_code")
        )

        # GraphQL specific attributes
        if self.attributes.get("component") and self.attributes.get("component").lower() == "graphql":
            self._graphql_attribute_mapping()
            
        # Add OTel attributes as custom NR trace attributes
        self._set_attributes_in_nr(self.attributes)

        error = sys.exc_info()
        self.set_status(StatusCode.OK if not error[0] else StatusCode.ERROR)

        # Only if unhandled exception do we want to abruptly end.
        # Otherwise, ensure that the span is the last one to end.
        if getattr(self.attributes, "exception.escaped", False) or (
            self.kind
            in (otel_api_trace.SpanKind.SERVER, otel_api_trace.SpanKind.CONSUMER)
            and isinstance(current_trace(), Sentinel)
        ):
            # We need to end the transaction, which will
            # end the sentinel trace as well.
            self.nr_transaction.__exit__(*error)
        else:
            # Just end the existing trace
            self.nr_trace.__exit__(*error)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ends context manager and calls `end` on the `Span`.
        This is used when span is called as a context manager
        i.e. `with tracer.start_span() as span:`
        """
        if exc_val and self.is_recording():
            if self._record_exception:
                self.record_exception(exception=exc_val, escaped=True)
            if self.set_status_on_exception:
                self.set_status(
                    Status(
                        status_code=StatusCode.ERROR,
                        description=f"{exc_type.__name__}: {exc_val}",
                    )
                )

        super().__exit__(exc_type, exc_val, exc_tb)


class Tracer(otel_api_trace.Tracer):
    def __init__(self, instrumentation_library=None, instrumenting_library_version=None, schema_url=None, attributes=None, resource=None, *args, **kwargs):
        self.instrumentation_library = instrumentation_library.split(".")[-1]
        self.instrumenting_library_version = instrumenting_library_version
        self.schema_url = schema_url
        self.tracer_attributes = attributes or {}
        self.resource = resource

    def _create_web_transaction(self, nr_headers=None):
        if "nr.wsgi.environ" in self.attributes:
            # This is a WSGI request
            transaction = WSGIWebTransaction(
                self.nr_application, environ=self.attributes.pop("nr.wsgi.environ")
            )
        elif "nr.asgi.scope" in self.attributes:
            # This is an ASGI request
            scope = self.attributes.pop("nr.asgi.scope")
            scheme = scope.get("scheme", "http")
            server = scope.get("server") or (None, None)
            host, port = scope["server"] = tuple(server)
            request_method = scope.get("method")
            request_path = scope.get("path")
            query_string = scope.get("query_string")
            headers = scope["headers"]
            transaction = WebTransaction(
                application=self.nr_application,
                name=self.name,
                group="Uri",
                scheme=scheme,
                host=host,
                port=port,
                request_method=request_method,
                request_path=request_path,
                query_string=query_string,
                headers=headers,
            )
        else:
            # This is a web request
            nr_headers = nr_headers or {}
            headers = self.attributes.pop("nr.http.headers", nr_headers)
            scheme = self.attributes.get("http.scheme")
            host = self.attributes.get("http.server_name")
            port = self.attributes.get("net.host.port")
            request_method = self.attributes.get("http.method")
            request_path = self.attributes.get("http.route")

            transaction = WebTransaction(
                self.nr_application,
                name=self.name,
                scheme=scheme,
                host=host,
                port=port,
                request_method=request_method,
                request_path=request_path,
                headers=headers,
            )
        return transaction

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
        self.attributes = {**(attributes or {}), **self.tracer_attributes, "schema_url": self.schema_url, "library_name": self.instrumentation_library, "library_version": self.instrumenting_library_version}
        self.name = name
        self.links = links or []

        if not self.nr_application.active:
            # Force application registration if not already active
            retry_application_activation(self.nr_application)

        self._record_exception = record_exception
        self.set_status_on_exception = set_status_on_exception

        if (
            not self.nr_application.settings.opentelemetry.enabled
        ):
            return otel_api_trace.INVALID_SPAN

        # Retrieve parent span
        parent_span_context = otel_api_trace.get_current_span(
            context
        ).get_span_context()

        # Set default value for whether the span
        # should create an analogous NR trace.
        create_nr_trace = True

        if parent_span_context is None or not parent_span_context.is_valid:
            parent_span_context = None

        parent_span_trace_id = None
        nr_headers = {}
        if parent_span_context and self.nr_application.settings.distributed_tracing.enabled:
            parent_span_trace_id = parent_span_context.trace_id
            if len(parent_span_context.trace_state) > 0:
                # If headers did not propagate from an existing transaction due
                # to no transaction existing at the time of extraction, the
                # traceparent and tracestate will still be available in the context.
                nr_headers["tracestate"] = parent_span_context.trace_state.to_header()
                parent_span_span_id = parent_span_context.span_id
                parent_span_trace_flag = parent_span_context.trace_flags
                nr_headers[
                    "traceparent"
                ] = f"00-{parent_span_trace_id:032x}-{parent_span_span_id:016x}-{'01' if parent_span_trace_flag else '00'}"

        if not self.nr_application.settings.opentelemetry.traces.enabled:
            create_nr_trace = False

        # If remote_parent, transaction must be created, regardless of kind type
        # Make sure we transfer DT headers when we are here, if DT is enabled
        if parent_span_context and parent_span_context.is_remote:
            if kind in (otel_api_trace.SpanKind.SERVER, otel_api_trace.SpanKind.CLIENT):
                transaction = self._create_web_transaction(nr_headers)
                if not self.nr_application.settings.opentelemetry.traces.enabled:
                    transaction.ignore_transaction = True
                transaction.__enter__()
                # If a transaction was already active, we want to create
                # an NR trace under the existing transaction.  Otherwise,
                # do not create a new NR trace, aside from the transaction's
                # root span.
                if transaction.enabled:
                    create_nr_trace = False
            elif kind in (
                otel_api_trace.SpanKind.PRODUCER,
                otel_api_trace.SpanKind.INTERNAL,
            ):
                transaction = BackgroundTask(self.nr_application, name=self.name)
                if not self.nr_application.settings.opentelemetry.traces.enabled:
                    transaction.ignore_transaction = True
                transaction.__enter__()
                # If a transaction was already active, we want to create
                # an NR trace under the existing transaction.  Otherwise,
                # do not create a new NR trace, aside from the transaction's
                # root span.
                if transaction.enabled:
                    create_nr_trace = False
            elif kind == otel_api_trace.SpanKind.CONSUMER:
                transaction = MessageTransaction(
                    library=self.instrumentation_library,
                    destination_type="Exchange", 
                    destination_name=self.name,
                    application=self.nr_application,
                    headers=nr_headers,
                )
                if not self.nr_application.settings.opentelemetry.traces.enabled:
                    transaction.ignore_transaction = True
                transaction.__enter__()
                # In the case of a Kafka consumer span, we do not want to create
                # a trace regardless of whether a transaction already existed.
                # This scenario should either create a transaction or use
                # the existing transaction and add additional attributes to it.
                create_nr_trace = False

            if not transaction.enabled:
                # We will reach this if there already was a transaction
                # active.  The attempt at creating a transaction will
                # create one where transaction.enabled == False, so
                # we do not want to pass an inactive transaction along.
                transaction = current_transaction()

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
                    transaction = self._create_web_transaction(nr_headers)

                    transaction._trace_id = (
                        f"{parent_span_trace_id:x}"
                        if parent_span_trace_id
                        else transaction.trace_id
                    )
                    if not self.nr_application.settings.opentelemetry.traces.enabled:
                        transaction.ignore_transaction = True
                    transaction.__enter__()
                    create_nr_trace = False
            elif kind == otel_api_trace.SpanKind.INTERNAL:
                if transaction:
                    nr_trace_type = FunctionTrace
                else:
                    return otel_api_trace.INVALID_SPAN
            elif kind == otel_api_trace.SpanKind.CLIENT:
                if transaction:
                    if self.attributes.get("http.url") or self.attributes.get(
                        "http.method"
                    ):
                        nr_trace_type = ExternalTrace
                    else:
                        nr_trace_type = DatastoreTrace
                else:
                    return otel_api_trace.INVALID_SPAN
            elif kind == otel_api_trace.SpanKind.CONSUMER:
                # NOTE for instrumenting a Kafka consumer span:
                # If a transaction already exists, do not create a new one
                # nor should we create a MessageTrace under it.  We do,
                # however, want to add additional attributes from this span
                # into the existing transaction.
                if transaction and (
                    getattr(self, "_create_consumer_trace", False)
                    or (self.instrumentation_library != "kafka")
                ):
                    # If transaction already exists and the
                    # _create_consumer_trace flag is set to True,
                    # then create a MessageTrace under it.
                    # Note that for Kafka, this flag will not be
                    # set, so we will not create a MessageTrace
                    nr_trace_type = MessageTrace
                else:
                    transaction = MessageTransaction(
                        library=self.instrumentation_library,
                        destination_type="Exchange", 
                        destination_name=self.name,
                        application=self.nr_application,
                        headers=nr_headers,
                    )
                    if not self.nr_application.settings.opentelemetry.traces.enabled:
                        transaction.ignore_transaction = True
                    transaction.__enter__()
                    # In the case of a Kafka consumer span, we do not want to create
                    # a trace regardless of whether a transaction already existed.
                    # This scenario should either create a transaction or use
                    # the existing transaction and add additional attributes to it.
                    if (self.instrumentation_library == "kafka") or not getattr(
                        self, "_create_consumer_trace", False
                    ):
                        create_nr_trace = False

                if self.instrumentation_library == "kafka":
                    # Whether a transaction exists or not, do not create a NR
                    # trace for the case of a consumer span.
                    create_nr_trace = False
            elif kind == otel_api_trace.SpanKind.PRODUCER:
                if transaction:
                    nr_trace_type = MessageTrace
                else:
                    return otel_api_trace.INVALID_SPAN

        # Start transactions in this method, but start traces
        # in Span.  Span function will take in some Span args
        # as well as info for NR applications/transactions
        span = Span(
            name=self.name,
            parent=parent_span_context,
            resource=self.resource,
            attributes=self.attributes,
            kind=kind,
            nr_transaction=transaction,
            nr_trace_type=nr_trace_type,
            instrumenting_module=self.instrumentation_library,
            record_exception=self._record_exception,
            set_status_on_exception=self.set_status_on_exception,
            create_nr_trace=create_nr_trace,
            links=links,
        )

        # Remove the tracer._create_consumer_trace flag since
        # the span is created now.
        if hasattr(self, "_create_consumer_trace"):
            delattr(self, "_create_consumer_trace")

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
            links=links,
        )

        with otel_api_trace.use_span(
            span,
            end_on_exit=end_on_exit,
            record_exception=record_exception,
            set_status_on_exception=set_status_on_exception,
        ) as current_span:
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
        return Tracer(
            *args,
            instrumentation_library=instrumenting_module_name,
            instrumenting_library_version=instrumenting_library_version,
            schema_url=schema_url,
            attributes=attributes,
            resource=self._resource,
            **kwargs,
        )
