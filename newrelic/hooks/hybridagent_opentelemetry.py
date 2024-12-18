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
from contextlib import contextmanager

# from opentelemetry.trace.status import Status, StatusCode
from opentelemetry import trace as otel_api_trace
from opentelemetry.sdk import trace as otel_sdk_trace
from opentelemetry.trace import Context, SpanKind
from opentelemetry.trace.propagation import _SPAN_KEY
from opentelemetry.trace.span import SpanContext, TraceFlags, TraceState

from newrelic.api.application import application_instance, register_application
from newrelic.api.background_task import BackgroundTask
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction, record_custom_metric
from newrelic.common.encoding_utils import NrTraceState  # , W3CTraceParent
from newrelic.common.object_wrapper import wrap_function_wrapper


# ----------------------------------------------
# Custom OTel Metrics
# ----------------------------------------------
class HistogramDict(dict):
    def __init__(self, value):
        self.value = value
        self.total = 0
        self.count = 0
        self.min = value
        self.max = value
        self.sum_of_squares = 0

        self.record_value()

    def __call__(self, value):
        self.value = value
        self.record_value()

    def set_total(self):
        self.total += self.value

    def set_count(self):
        self.count += 1

    def set_min(self):
        self.min = min(self.min, self.value)

    def set_max(self):
        self.max = max(self.max, self.value)

    def set_sum_of_squares(self):
        self.sum_of_squares += self.value**2

    def record_value(self):
        self.set_total()
        self.set_count()
        self.set_min()
        self.set_max()
        self.set_sum_of_squares()

        self["total"] = self.total
        self["count"] = self.count
        self["min"] = self.min
        self["max"] = self.max
        self["sum_of_squares"] = self.sum_of_squares

        return self


def wrap_meter(wrapped, instance, args, kwargs):
    def bind_meter(name, version=None, schema_url=None, *args, **kwargs):
        return name, version, schema_url  # attributes

    name, version, schema_url = bind_meter(*args, **kwargs)

    if schema_url:
        record_custom_metric(f"OtelMeter/{name}/SchemaURL/{schema_url}", 1)
    if version:
        record_custom_metric(f"OtelMeter/{name}/{version}", 1)
    else:
        record_custom_metric(f"OtelMeter/{name}", 1)

    return wrapped(*args, **kwargs)


def wrap_add(wrapped, instance, args, kwargs):
    def bind_add(amount, *args, **kwargs):
        return amount  # , attributes, context

    amount = bind_add(*args, **kwargs)
    meter_name = instance.instrumentation_scope.name
    counter_name = instance.name

    record_custom_metric(f"OtelMeter/{meter_name}/{counter_name}", {"count": amount})

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

    meter_name = instance.instrumentation_scope.name
    histogram_name = instance.name
    histogram_reference = f"OtelMeter/{meter_name}/{histogram_name}"

    if transaction._histogram and histogram_reference in transaction._histogram:
        # We are adding to the existing histogram
        transaction._histogram[histogram_reference](amount)
    else:
        # Creating a new histogram instance
        transaction._histogram[histogram_reference] = HistogramDict(amount)

    return wrapped(*args, **kwargs)


def _instrument_observable_methods(module, method_name):
    def wrap_observable_method(wrapped, instance, args, kwargs):
        def bind_func(name, callbacks, unit=None, *args, **kwargs):
            return name, callbacks, unit

        method_name, callbacks, unit = bind_func(*args, **kwargs)
        meter_name = instance._instrumentation_scope.name

        for callback in callbacks:
            for observation in callback():
                metric_value = (
                    f"OtelMeter/{meter_name}/{method_name}"
                    if not unit
                    else f"OtelMeter/{meter_name}/{method_name}/{unit}"
                )
                if method_name.endswith("gauge"):
                    record_custom_metric(metric_value, observation.value)
                else:
                    record_custom_metric(metric_value, {"count": observation.value})

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
# Custom OTel Spans
# ----------------------------------------------

# TracerProvider: we can think of this as the agent instance.  Only one can exist
# SpanProcessor: we can think of this as an application.  In NR, we can have multiple applications
#   though right now, we can only do SpanProcessor and SynchronousMultiSpanProcessor
# Tracer: we can think of this as the transaction.
# Span: we can think of this as the trace.
# Links do not exist in NR.  Links are relationships between spans, but lateral in
#   hierarchy.  In NR we only have parent-child relationships.

# Our objectives:
# 1. Create a wrapper around the Otel SDK Span object to match NR Trace object
#   (same as what has been done).  This scenario covers when there's no NR
#   instrumentation and all instrumentation is in Otel.
# 2. Create a wrapper around the NR Trace object to match the Otel SDK Span object.
#   This scenario covers when there's no Otel instrumentation and all instrumentation
#   is in NR and we want to pass that data to Otel.
#   - This may help when we are covering our edge case mentioned below:

# Edge case scenarios to account for:
# 1. If some instrumentation is in Otel and some is in NR, we need to be able to
#    keep track of the parent, context, et cetera
#    a. NR to Otel instrumentation propagation
#    b. Otel to NR instrumentation propagation

# A wrapper around a NR Time Trace object to match the Otel SDK Span object--
# This will take spans passed in Otel format and allow conversion to NR format

# Eventually we need to monkey patch these so that they operate "out of the box"
# instead of having to explicitly import these specific classes in lieu of the
# Otel SDK classes.


class Span(otel_sdk_trace.Span):
    def __init__(
        self,
        name,
        nr_trace=None,
        nr_application=None,
        record_exception=True,
        attributes=None,
    ):
        self._name = name
        self.nr_trace = nr_trace if nr_trace else current_trace()
        self.nr_application = nr_application if nr_application else application_instance(activate=False)
        self._context = self.get_span_context()  # attempt to fix the inheritance issue
        self.otel_context = Context({_SPAN_KEY: self})  # This will be the Otel span context
        self._record_exception = (
            record_exception or self.nr_trace.settings.error_collector.record_exception
        )  # both must be set to false in order to not record
        self._status = 0  # UNSET (Otel statuses are not a 1:1 mapping)
        self._attributes = self._set_attributes_in_nr(attributes)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end(exception=(exc_type, exc_val, exc_tb))

    def _is_sampled(self):
        # returns appropriate TraceFlag, depending on
        # whether the transaction is sampled or not
        return (
            TraceFlags.SAMPLED
            if (self.nr_trace.transaction.sampled and not self.nr_trace.transaction.ignore_transaction)
            else TraceFlags.DEFAULT
        )

    def get_span_context(self):
        nr_headers = self.nr_trace.transaction._create_distributed_trace_data()
        trusted_account_key = self.nr_trace.transaction._settings.trusted_account_key or (
            self.nr_trace.transaction._settings.serverless_mode.enabled
            and self.nr_trace.transaction._settings.account_id
        )
        nr_tracestate_headers = NrTraceState.decode(NrTraceState(nr_headers).text(), trusted_account_key)

        # Convert from dict to list of key/value tuples
        otel_tracestate_headers = [(key, value) for key, value in nr_tracestate_headers.items()]

        # breakpoint()
        return SpanContext(
            trace_id=int(self.nr_trace.transaction.guid, 16),
            span_id=int(self.nr_trace.guid, 16),
            is_remote=False,  # This might be true when otel->nr or nr->otel instrumentation is implemented
            trace_flags=self._is_sampled(),
            trace_state=TraceState(otel_tracestate_headers),
        )

    def _set_attributes_in_nr(self, otel_attributes):
        if not otel_attributes:
            return
        for key, value in otel_attributes.items():
            # Distinguish between Otel and NR?  Or just
            # potentially override existing NR attributes
            # with Otel attributes?  For now, we will
            # add a key to the Otel attribute to distinguish
            # between the two
            otel_key = f"otel_attribute_{key}"  # may remove this all together
            self.nr_trace.add_custom_attribute(otel_key, value)

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
        self.nr_trace.notice_error(exception, attributes=attributes)


# A wrapper around a NR Transaction object to match the Otel SDK Tracer object--
# This will take tracers passed in Otel format and allow conversion to NR format
class Tracer(otel_sdk_trace.Tracer):
    def __init__(self, *args, nr_application=None, **kwargs):
        self._settings = None
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

    def _convert_span_context_to_trace(self, span_context):
        # Convert Otel SpanContext to NR SpanContext
        # This will be used to create a new trace in NR
        guid = span_context.trace_id
        trace_id = span_context.span_id
        sampled = span_context.trace_flags == TraceFlags.SAMPLED

    # Elastic's logic:
    # if traceparent and transaction, invalid
    # if traceparent, begin transaction, trace (with traceparent as parent trace), and span
    # if not transaction, begin transaction, trace, and span
    # else, begin trace and span

    def start_span(self, name, context=None, kind=SpanKind.INTERNAL, attributes=None, record_exception=True):
        parent_span_context = otel_api_trace.get_current_span(context).get_span_context()
        nr_parent_trace = current_trace() or (self.nr_transaction and self.nr_transaction.root_span)

        # This filters out any scenarios where otel does not actually exist yet
        if parent_span_context is None or not parent_span_context.is_valid:
            parent_span_context = None

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
            )
        elif parent_span_context and self.nr_transaction:
            # This is a scenario where we are coming in from Otel into the NR space
            # Several possibilities exist here:
            # 1. if parent_span_context.trace_id has 0x0000 in front, it is NR transaction.guid.  Else it is Otel trace_id
            #   a. If it is == to NR transaction.guid, we just need to start a trace/span (transition already in progress)
            #   b. If it is Otel trace_id or not the same NR transaction.guid, something has gone out of sync.  This might need more investigation
            # 2. if self.nr_transaction.root_span == nr_parent_trace, we have not started a trace
            # in the NR space yet.  However, there exists a parent_span_context, so spans have been started in Otel.
            # In this case, we need to create trace nodes in NR to connect otel to NR.  After that, we can
            # start a trace/span in NR/otel, respectively.
            pass
        elif parent_span_context and not self.nr_transaction:
            # Another scenario where we are coming in from Otel into the NR space
            # Here we need to go up the parent span context all the way up to the root span
            # and create trace nodes in NR to connect otel to NR.  After that, we can start
            # a transaction and override the start time of the transaction to match the start
            # time of the root span.  Then we can start a trace/span in NR/otel, respectively.
            pass
            # parent_trace = None     # COME BACK TO THIS
            # self.nr_transaction = BackgroundTask(application=self.nr_application, name=name, group="Otel")
            # nr_trace = FunctionTrace(name=name, group="Otel", parent=parent_trace, record_exception=record_exception, attributes=attributes)
            # span = Span(name=name, parent=parent_span_context, nr_trace=nr_trace, nr_application=self.nr_application, record_exception=record_exception, attributes=attributes)

        # span.set_attributes(attributes) # Do we really need to retain otel attributes once we are in NR?

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
    def _use_span(self, span, end_on_exit=False, record_exception=True):
        try:
            yield span
        except Exception as exc:
            if record_exception:
                span.record_exception(exc)
            raise
        finally:
            span.end()
            # IGNORE end_on_exit FOR NOW
            # if end_on_exit:
            #     span.end()

    @contextmanager
    def start_as_current_span(
        self, name, context=None, kind=SpanKind.INTERNAL, attributes=None, end_on_exit=True, record_exception=True
    ):
        span = self.start_span(
            name, context=context, kind=kind, attributes=attributes, record_exception=record_exception
        )

        with self._use_span(span, end_on_exit=True, record_exception=record_exception) as current_span:
            yield current_span


# In OTel, this is within a TracerProvider.  TracerProviders allow the option to have
# multiple Tracers.  In NR, we only have one TracerProvider (Agent instance), so these
# will be functions, rather than methods within a class.
def get_tracer(tracer_name, nr_application=None):
    return Tracer(tracer_name, nr_application=nr_application)
