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

# import enum
import sys

# from opentelemetry.trace.status import Status, StatusCode
from opentelemetry import trace as otel_api_trace
from opentelemetry.context import Context
from opentelemetry.sdk import trace as otel_sdk_trace
from opentelemetry.trace.propagation import _SPAN_KEY
from opentelemetry.trace.span import SpanContext, TraceFlags, TraceState

from newrelic.api.application import application_instance

# from newrelic.api.background_task import BackgroundTask, BackgroundTaskWrapper
# from newrelic.api.function_trace import FunctionTrace, FunctionTraceWrapper
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction, record_custom_metric

# from newrelic.common.object_names import callable_name
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

# Trace IDs --> transaction
# Span IDs --> traces

# We can use elastic APM as a reference for how to handle this

# https://github.com/elastic/apm-agent-python/blob/main/elasticapm/contrib/opentelemetry/span.py
# https://github.com/elastic/apm-agent-python/blob/main/elasticapm/contrib/opentelemetry/trace.py


# Elasic's Otel bridge assume all Otel and converts that to Elastic
# they use a wrapper around the Otel Span and have outgoing functions
# and initializations that match the Otel convention that override into
# Elastic's conventions.
# Otel -> Elastic

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
class Span(otel_sdk_trace.Span):
    def __init__(
        self,
        *args,
        name,
        parent=None,
        nr_trace=None,
        nr_application=None,
        record_exception=True,
        attributes=None,
        **kwargs,
    ):
        self._name = name
        self.nr_trace = nr_trace or current_trace()
        self.nr_application = nr_application or application_instance(activate=False)
        # nr_trace.otel_wrapper = self  # COME BACK TO THIS
        self.otel_parent = parent  # If this exists, this will be the Otel parent span
        self.otel_context = Context({_SPAN_KEY: self})  # This will be the Otel span context
        self._record_exception = (
            record_exception or self.nr_trace.settings.error_collector.record_exception
        )  # both have to be set to false in order to not record
        self._status = 0  # UNSET (Otel statuses are not a 1:1 mapping)
        self.attributes = attributes or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end(exception=(exc_type, exc_val, exc_tb))

    def _is_sampled(self):
        # returns appropriate TraceFlag, depending on
        # whether the transaction is sampled or not
        return (
            TraceFlags.SAMPLED
            if (self.nr_trace.transaction.sampled and self.nr_trace.transaction.ignore_transaction)
            else TraceFlags.DEFAULT
        )

    def get_span_context(self):
        nr_headers = []
        nr_headers.extend(self.nr_trace.transaction._generate_distributed_trace_headers())
        # (header_type, headers) where header_type is a string and headers is a list of tuples
        nr_tracestate_headers = [
            (key, value)
            for header_type, headers in nr_headers
            if header_type.lower() == "tracestate"
            for key, value in headers
        ]

        return SpanContext(
            trace_id=self.nr_trace.transaction.guid,
            span_id=self.nr_trace.guid,
            is_remote=False,  # This is always false for New Relic
            trace_flags=self._is_sampled(),  # TraceFlags.SAMPLED if self.nr_trace.transaction.sampled else TraceFlags.DEFAULT,
            trace_state=TraceState(nr_tracestate_headers),
        )

    def _set_attributes_in_nr(self, otel_attributes):
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
        pass  # Not implemented yet.

    # def start(self, start_time=None, parent_context=None):
    #     # Check to see if self.nr_trace and self.nr_transaction are active
    #     if not self.nr_transaction:
    #         # Create a new transaction
    #         self.nr_transaction = BackgroundTask(application=application_instance(), name=self._name)
    #         self.nr_transaction.__enter__()

    #     if not self.nr_trace:
    #         # Create a new trace and set the parent of that trace as
    #         # root span created by the transaction
    #         self.nr_trace = FunctionTrace(name=self._name, parent=self.nr_transaction.root_span) #, source=self.__wrapped__.__enter__)

    #     # Check to see if trace already started
    #     if self.nr_trace.start_time:
    #         return

    #     self.nr_trace.__enter__()

    #     # At what point do we abandon the Otel convention and go to NR?
    #     # Elastic only overrides the outgoing functions to reflect their
    #     # conventions, but the incoming functions, such as start, are still Otel
    #     super().start(start_time, parent_context)

    def end(self, end_time=None, exception=(None, None, None)):
        # For now, we will ignore the end_time parameter

        # Check to see if trace already ended
        if self.nr_trace.end_time:
            return

        # Update trace name before ending
        self.nr_trace.update_name(self._name)

        # Add attributes as FunctionTrace parameters
        self._set_attribute_in_nr(self.attributes)

        # Grab current transaction before exiting the trace
        # in case it is the last trace
        current_transaction = self.nr_trace.transaction

        exc = exception if (exception[0] or exception[1] or exception[2]) else sys.exc_info()
        self.nr_trace.__exit__(*exc)

        # If this is the last trace, end the transaction
        if current_transaction.root == current_trace():
            current_transaction.__exit__(*exc)

    def update_name(self, name):
        self._name = name
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
        self.nr_application = nr_application or application_instance(activate=False)
        if not self.nr_application:
            global_settings = self.nr_application.global_settings


class OtelTransaction(otel_sdk_trace.Tracer):
    def __init__(self, *args, application=None, enabled=None, source=None, **kwargs):
        # original args: sampler, resource, span_processor, id_generator, instrumentation_info, span_limits, instrumentation_scope
        self.application = application
        # Insert logic here to get application if one is not passed in
        self.enabled = enabled
        self.source = source

    def start_span(
        self,
        name,
        context=None,
        kind=otel_api_trace.SpanKind.INTERNAL,
        attributes=None,
        links=None,
        start_time=None,
        record_exception=True,
        set_status_on_exception=True,
    ):
        # original args: name, context, kind, attributes, links, start_time, record_exception, set_status_on_exception
        pass
