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

import sys
import uuid
from contextlib import contextmanager

# from opentelemetry.trace.status import Status, StatusCode
from opentelemetry import trace as otel_api_trace
from opentelemetry.trace import Context, SpanKind
from opentelemetry.trace.propagation import _SPAN_KEY
from opentelemetry.trace.span import INVALID_SPAN, SpanContext, TraceFlags, TraceState

from newrelic.api.application import application_instance, register_application
from newrelic.api.background_task import BackgroundTask
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import (
    current_transaction,
    record_custom_metric,
    record_dimensional_metric,
)
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.wsgi_application import WSGIWebTransaction
from newrelic.common.encoding_utils import NrTraceState
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.trace_cache import trace_cache


# ----------------------------------------------
# Custom OTel Metrics
# ----------------------------------------------
def wrap_meter(wrapped, instance, args, kwargs):
    def bind_meter(name, version=None, schema_url=None, *args, **kwargs):
        return name, version, schema_url  # attributes

    transaction = current_transaction()
    name, version, schema_url = bind_meter(*args, **kwargs)
    settings = (transaction and transaction.settings) or application_instance().settings

    custom_metric_function = (
        record_custom_metric if not settings.otel_dimensional_metrics.enabled else record_dimensional_metric
    )

    if schema_url:
        custom_metric_function(f"OtelMeter/{name}/SchemaURL/{schema_url}", 1)
    if version:
        custom_metric_function(f"OtelMeter/{name}/{version}", 1)
    else:
        custom_metric_function(f"OtelMeter/{name}", 1)

    return wrapped(*args, **kwargs)  # Do we even need to do this?


def wrap_add(wrapped, instance, args, kwargs):
    def bind_add(amount, *args, **kwargs):
        return amount  # , attributes, context

    transaction = current_transaction()
    amount = bind_add(*args, **kwargs)
    meter_name = instance.instrumentation_scope.name
    counter_name = instance.name

    settings = (transaction and transaction.settings) or application_instance().settings

    custom_metric_function = (
        record_custom_metric if not settings.otel_dimensional_metrics.enabled else record_dimensional_metric
    )

    custom_metric_function(f"OtelMeter/{meter_name}/{counter_name}", {"count": amount})

    return wrapped(*args, **kwargs)


def wrap_record(wrapped, instance, args, kwargs):
    def bind_record(amount, *args, **kwargs):
        return amount  # attributes, context

    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    amount = bind_record(*args, **kwargs)
    meter_name = instance.instrumentation_scope.name
    histogram_name = instance.name

    settings = (transaction and transaction.settings) or application_instance().settings

    custom_metric_function = (
        record_custom_metric if not settings.otel_dimensional_metrics.enabled else record_dimensional_metric
    )

    custom_metric_function(f"OtelMeter/{meter_name}/{histogram_name}", amount)

    return wrapped(*args, **kwargs)


def _instrument_observable_methods(module, method_name):
    def wrap_observable_method(wrapped, instance, args, kwargs):
        def bind_func(name, callbacks, unit=None, *args, **kwargs):
            return name, callbacks, unit

        transaction = current_transaction()

        method_name, callbacks, unit = bind_func(*args, **kwargs)
        meter_name = instance._instrumentation_scope.name
        settings = (transaction and transaction.settings) or application_instance().settings

        custom_metric_function = (
            record_custom_metric if not settings.otel_dimensional_metrics.enabled else record_dimensional_metric
        )

        for callback in callbacks:
            for observation in callback():
                metric_value = (
                    f"OtelMeter/{meter_name}/{method_name}"
                    if not unit
                    else f"OtelMeter/{meter_name}/{method_name}/{unit}"
                )
                if method_name.endswith("gauge"):
                    custom_metric_function(metric_value, observation.value)
                else:
                    custom_metric_function(metric_value, {"count": observation.value})

        return wrapped(*args, **kwargs)

    wrap_function_wrapper(module, f"Meter.{method_name}", wrap_observable_method)


def instrument_observable_methods(module, observable_method_functions):
    for method_name in observable_method_functions:
        _instrument_observable_methods(module, method_name)


def instrument_meter(module):
    if hasattr(module, "MeterProvider"):
        wrap_function_wrapper(module, "MeterProvider.get_meter", wrap_meter)

    if hasattr(module, "Counter"):
        wrap_function_wrapper(module, "Counter.add", wrap_add)
    if hasattr(module, "UpDownCounter"):
        wrap_function_wrapper(module, "UpDownCounter.add", wrap_add)

    if hasattr(module, "Histogram"):
        wrap_function_wrapper(module, "Histogram.record", wrap_record)

    if hasattr(module, "Meter"):
        observable_method_functions = (
            "create_observable_gauge",
            "create_observable_counter",
            "create_observable_up_down_counter",
        )
        instrument_observable_methods(module, observable_method_functions)


# ----------------------------------------------
# Custom OTel Context Propagation
# ----------------------------------------------
class ContextApi:
    def create_key(self, keyname):
        return keyname + "-" + str(uuid.uuid4())

    def get_value(self, key, context=None):
        return context.get(key) if context else self.get_current().get(key)

    def set_value(self, key, value="value", context=None):
        if context is None:
            context = self.get_current()
        new_values = context.copy()
        new_values[key] = value
        return Context(new_values)

    def get_current(self):
        trace = current_trace()
        if not trace:
            return Context()

        # Convert NR trace into Otel Span
        if hasattr(trace, "otel_wrapper") and getattr(trace, "otel_wrapper"):
            # Make sure trace.otel_wrapper actually has a value and isn't just set to None
            otel_span = trace.otel_wrapper
        else:
            # Create a new Otel Span
            otel_span = Span(name=getattr(trace, "name", "Sentinel"), nr_trace=trace)
        context = otel_span.otel_context

        return context

    def attach(self, context):
        # Original function returns a token.
        span = context.get(_SPAN_KEY)  # Where does create_key even get used?
        if not span:
            return None
        span.otel_context = context
        nr_trace = span.nr_trace

        # If not already the current trace, push it to the cache
        cache = trace_cache()
        if nr_trace.thread_id != cache.current_thread_id():
            nr_trace.thread_id = cache.current_thread_id()
            cache.save_trace(nr_trace)

        return None

    def detach(self, token=None):
        # Original function takes a token.  We will ignore this value.
        nr_trace = current_trace()
        if nr_trace:
            cache = trace_cache()
            cache.pop_current(nr_trace)
        else:
            pass  # Log this


# ----------------------------------------------
# Custom OTel Spans
# ----------------------------------------------

# TracerProvider: we can think of this as the agent instance.  Only one can exist (in both NR and Otel)
# SpanProcessor: we can think of this as an application.  In NR, we can have multiple applications
#   though right now, we can only do SpanProcessor and SynchronousMultiSpanProcessor
# Tracer: we can think of this as the transaction.
# Span: we can think of this as the trace.
# Links do not exist in NR.  Links are relationships between spans, but lateral in
#   hierarchy.  In NR we only have parent-child relationships.  We might want to
#   preserve this information with a custom attribute.  We can also add this as a
#   new attribute in a trace, but it will still not be seen in the UI other than a
#   trace attribute


class Span(otel_api_trace.Span):
    def __init__(
        self,
        name,
        nr_trace=None,
        nr_application=None,
        record_exception=True,
        attributes=None,
        kind=SpanKind.INTERNAL,
        *args,
        **kwargs,
    ):
        self._name = name
        self.nr_trace = nr_trace if nr_trace else current_trace()
        self.nr_application = nr_application if nr_application else application_instance(activate=False)
        self.otel_context = Context({_SPAN_KEY: self})  # This will be the Otel span context
        nr_trace.otel_wrapper = self
        self._record_exception = (
            record_exception or self.nr_trace.settings.error_collector.enabled
        )  # both must be set to false in order to not record
        self._status = 0  # UNSET (Otel statuses are not a 1:1 mapping)
        self._attributes = attributes if attributes else {}
        self.kind = kind

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end(exception=(exc_type, exc_val, exc_tb))

    def _is_sampled(self):
        # Uses NR to determine if the trace is sampled
        sampled = bool(self.nr_trace.transaction.sampled and not self.nr_trace.transaction.ignore_transaction)
        return sampled

    def get_span_context(self):
        nr_headers = self.nr_trace.transaction._create_distributed_trace_data()
        trusted_account_key = self.nr_trace.transaction._settings.trusted_account_key or (
            self.nr_trace.transaction._settings.serverless_mode.enabled
            and self.nr_trace.transaction._settings.account_id
        )
        nr_tracestate_headers = NrTraceState.decode(NrTraceState(nr_headers).text(), trusted_account_key)

        # Convert from dict to list of key/value tuples
        otel_tracestate_headers = [(key, str(value)) for key, value in nr_tracestate_headers.items()]

        return SpanContext(
            trace_id=int(self.nr_trace.transaction.guid, 16),
            span_id=int(self.nr_trace.guid, 16),
            is_remote=False,  # TODO: This can be thought of as an orphaned span flag.  Come back to this
            trace_flags=TraceFlags(self._is_sampled()),  # self._is_sampled(),
            trace_state=TraceState(otel_tracestate_headers),
        )

    def set_attribute(self, key, value):
        self._attributes[key] = value

    def set_attributes(self, attributes):
        for key, value in attributes.items():
            self.set_attribute(key, value)

    def _set_attributes_in_nr(self, otel_attributes):
        if not otel_attributes:
            return
        for key, value in otel_attributes.items():
            # Distinguish between Otel and NR?  Or just
            # potentially override existing NR attributes
            # with Otel attributes?  For now, we will
            # override the attributes if there is a duplicate
            self.nr_trace.add_custom_attribute(key, value)

    def add_event(self, name, attributes=None, timestamp=None):
        # We can implement this as a log event
        pass  # Not implemented yet.

    def add_link(self, span_context, attributes=None):
        pass  # Not implemented.  NR does not have this functionality

    def end(self, end_time=None, exception=(None, None, None)):
        # For now, we will ignore the end_time parameter

        # Check to see if trace already ended
        if self.nr_trace.end_time:
            return

        # # Update trace name before ending
        self.update_name(self._name)

        # Add attributes as FunctionTrace/Sentinel parameters
        self._set_attributes_in_nr(self._attributes)

        # Set SpanKind attribute
        self._set_attributes_in_nr({"span.kind": self.kind})

        # Store current transaction and trace before exiting
        # the trace in case it is the last trace
        current_transaction = self.nr_trace.transaction
        current_trace = self.nr_trace

        exc = exception if (exception[0] or exception[1] or exception[2]) else sys.exc_info()
        self.nr_trace.__exit__(*exc)

        # If this was the last trace, end the transaction
        if current_transaction.root_span == current_trace:
            current_transaction.__exit__(*exc)

    def update_name(self, name):
        self._name = name
        if hasattr(self.nr_trace, "name"):  # Sentinel traces do not have a name attribute
            self.nr_trace.name = self._name

    def is_recording(self):
        return self._is_sampled() and not self.nr_trace.end_time

    def set_status(self, status):
        # Not implemented yet
        pass

    # # DO WE EVEN NEED THIS?
    # def _otel_to_nr_status(self, status):
    #     """
    #     # NR transactions have
    #     # STATE_PENDING = 0
    #     # STATE_RUNNING = 1
    #     # STATE_STOPPED = 2
    #     # NR traces have
    #     # self.activated and self.exited
    #     # Otel spans have
    #     # UNSET = 0
    #     # OK = 1
    #     # ERROR = 2

    #     # NR->OTEL status conversion
    #     # UNSET = self.nr_trace.transaction.state == 0 or self.nr_trace.transaction.state == 1 or self.nr_trace.activated
    #     # OK = (self.nr_trace.transaction.state == 2 or self.nr_trace.exited) and not self.nr_trace.exc_data
    #     # ERROR = self.nr_trace.exited and self.nr_trace.exc_data

    #     # OTEL->NR status conversion
    #     # STATE_PENDING = status.status_code is StatusCode.UNSET
    #     # STATE_RUNNING = status.status_code is StatusCode.UNSET
    #     # STATE_STOPPED = status.status_code is StatusCode.ERROR or status.status_code is StatusCode.OK
    #     """
    #     pass

    # # NOT COMPLETE (figure out how to handle error->OK transitions)
    # def set_status(self, status, description=None):
    #     """
    #     Set the status of the Span. If used, this will override the default Span status.
    #     Note that statuses can be set laterally or forward, timewise.  That is to say
    #     that a status cannot be set to UNSET nor can it be set if the status is already OK.
    #         Valid paths:
    #         UNSET ->    ERROR
    #         ERROR ->    OK
    #         UNSET ->    OK

    #         status (Status): tuple of (StatusCode, str|None) where StatusCode is type enum
    #         description (str): description of the error (only used if status.status_code is ERROR)
    #     """

    #     if (self._status and self._status.status_code is StatusCode.OK) or status.status_code is StatusCode.UNSET:
    #         return      # Status is already OK or attempting to set status to UNSET
    #     elif isinstance(status, Status):
    #         # If description exists, we ignore it.  We might add a log message to indicate this
    #         self._status = status
    #         # if conversation was ERROR->OK, we should add ignore error to the trace
    #     elif isinstance(status, StatusCode):    # Should be used for errors with description
    #         self._status = Status(status, description)
    #         # if UNSET->ERROR, we should add error to the trace, exit the trace, and
    #         # try to find *sys.exc_info to pass to __exit__.  If no *sys.exc_info, we should
    #         # create a new exception and pass that to __exit__.
    #         if status is StatusCode.ERROR:
    #             try:
    #                 raise Exception(description)
    #             except Exception as exc:
    #                 self.record_exception(exc)

    def record_exception(self, exception, attributes=None, timestamp=None, escaped=False):
        self.nr_trace.notice_error((type(exception), exception, exception.__traceback__), attributes=attributes)


class Tracer(otel_api_trace.Tracer):
    def __init__(self, *args, nr_application=None, **kwargs):
        self._settings = None
        self.context_api = ContextApi()
        self.nr_application = (
            nr_application or application_instance(activate=False) or register_application("OtelTracer")
        )
        self.global_settings = self.nr_application and self.nr_application.global_settings
        self.nr_transaction = current_transaction()  # This will be the NR transaction

        if self.nr_application and self.global_settings.enabled and self.nr_application.enabled:
            self._settings = self.nr_application.settings
            if not self._settings:
                self.nr_application.activate()
                self._settings = self.nr_application.settings
        else:
            # Unable to register application.  We should log this.
            pass

    def _kind_identifier(self, transaction):
        """
        Kind identifier:
        - SERVER: Incoming HTTP request or RPC
        - CLIENT: Outgoing HTTP request
        - PRODUCER: Producer/creator of a job
        - CONSUMER: Consumer/processor of a job
        - INTERNAL: Internal operation
        """
        if isinstance(transaction, WSGIWebTransaction):
            kind = SpanKind.SERVER
        elif isinstance(transaction, WebTransaction):
            kind = SpanKind.CLIENT
        else:
            kind = SpanKind.INTERNAL
        return kind

    def start_span(
        self,
        name,
        context=None,
        kind=SpanKind.INTERNAL,
        start_time=None,
        attributes=None,
        record_exception=True,
        set_status_on_exception=True,
    ):
        nr_parent_trace = current_trace() or (self.nr_transaction and self.nr_transaction.root_span)

        # Check again for the current transaction if it was not set in __init__
        self.nr_transaction = current_transaction() if not self.nr_transaction else self.nr_transaction

        kind = self._kind_identifier(self.nr_transaction) if kind == SpanKind.INTERNAL else kind

        # Modified Otel Span to include New Relic Trace
        if nr_parent_trace and nr_parent_trace.otel_wrapper:
            parent_span_context = nr_parent_trace.otel_wrapper.get_span_context()
        # Original New Relic Trace
        else:
            parent_span_context = None

        # We might still need this logic for when there is otel coming into NR
        # i.e. there may be a current trace, but no New Relic transaction/trace yet?
        # parent_span_context = otel_api_trace.get_current_span(context).get_span_context()
        # This filters out any scenarios where otel does not actually exist yet
        # if parent_span_context is None or not parent_span_context.is_valid:
        #     parent_span_context = None

        # Use parent_span_context to
        # 1) create headers for DT mode and
        # 2) create parent trace nodes by converting parent_span_context into a New Relic parent trace
        # This has to be a trace and not the node because it's still in progress
        # We will create this trace and then modify the start time to match the start time of the current span

        if not parent_span_context and not self.nr_transaction:
            # No transaction exists, so we need to start a transaction and a trace/span
            self.nr_transaction = BackgroundTask(application=self.nr_application, name=name, group="Otel")
            self.nr_transaction.__enter__()
            nr_trace = self.nr_transaction.root_span
            nr_trace.__enter__()
            span = Span(
                name=name,
                nr_trace=nr_trace,
                nr_application=self.nr_application,
                record_exception=record_exception,
                attributes=attributes,
                kind=kind,
            )
        elif not parent_span_context and self.nr_transaction:
            # we need to start a trace/span
            nr_trace = FunctionTrace(name=name, group="Otel", parent=nr_parent_trace, params=attributes)
            nr_trace.__enter__()
            span = Span(
                name=name,
                nr_trace=nr_trace,
                nr_application=self.nr_application,
                record_exception=record_exception,
                attributes=attributes,
                kind=kind,
            )
        elif parent_span_context and self.nr_transaction:
            nr_trace = FunctionTrace(name=name, group="Otel", parent=nr_parent_trace, params=attributes)
            nr_trace.__enter__()
            span = Span(
                name=name,
                nr_trace=nr_trace,
                nr_application=self.nr_application,
                record_exception=record_exception,
                attributes=attributes,
                kind=kind,
            )
        elif parent_span_context and not self.nr_transaction:
            # Current the way this is written, we will never hit this block
            # breakpoint()  # Keep this here in case it ever does get here.
            span = Span(
                name=name,
                nr_application=self.nr_application,
                record_exception=record_exception,
                attributes=attributes,
                kind=kind,
            )

        # If DT is enabled, get DT headers
        if self._settings.distributed_tracing.enabled:
            # COME BACK TO THIS WHEN WE ARE READY TO IMPLEMENT DISTRIBUTED TRACING
            # headers = self._settings.distributed_tracing.create_distributed_trace_headers()
            # transaction.insert_distributed_trace_headers(headers)
            # use parent_span_context to create headers
            # from here, we need to convert Otel SpanContext to NR SpanContext
            pass

        return span

    @contextmanager
    def _use_span(self, span, end_on_exit=True, record_exception=True):
        self.context_api.attach(self.context_api.set_value(_SPAN_KEY, span))
        try:
            yield span
        except Exception as exc:
            if record_exception:
                span.record_exception(exc)
            raise
        finally:
            if end_on_exit:
                span.end()
            else:
                self.context_api.detach()

    @contextmanager
    def start_as_current_span(
        self,
        name,
        context=None,
        kind=SpanKind.INTERNAL,
        attributes=None,
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

        with self._use_span(span, end_on_exit=end_on_exit, record_exception=record_exception) as current_span:
            yield current_span


def wrap_get_tracer(wrapped, instance, args, kwargs):
    # Ignore module_name for now.  We will come back to this.
    # This module name will be part of the function metric name.
    # Instrumenting library version can be added to the metric
    # name as well; it can also be populated with the package
    # finder function.
    # schema_url will be a custom transaction attribute
    # attributes will be custom transaction attributes

    def bind_get_tracer(instrumenting_module_name, *args, **kwargs):
        return instrumenting_module_name

    module_name = bind_get_tracer(*args, **kwargs)

    return Tracer(module_name)


def wrap_use_span(wrapped, instance, args, kwargs):
    tracer = otel_api_trace.get_tracer(__name__)
    return tracer._use_span(*args, **kwargs)


def wrap_get_current_span(wrapped, instance, args, kwargs):
    tracer = otel_api_trace.get_tracer(__name__)
    current_span = tracer.context_api.get_value(_SPAN_KEY)

    return current_span if current_span else INVALID_SPAN


def instrument_TracerProvider_get_tracer(module):
    if hasattr(module, "TracerProvider"):
        wrap_function_wrapper(module, "TracerProvider.get_tracer", wrap_get_tracer)


def instrument_trace_api(module):
    if hasattr(module, "use_span"):
        wrap_function_wrapper(module, "use_span", wrap_use_span)

    if hasattr(module, "get_current_span"):
        wrap_function_wrapper(module, "get_current_span", wrap_get_current_span)
