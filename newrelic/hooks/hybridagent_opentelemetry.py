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
import os
import time

from newrelic.api.application import application_instance
from newrelic.api.time_trace import add_custom_span_attribute, current_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)
_TRACER_PROVIDER = None

# Enable OpenTelemetry Bridge to capture HTTP
# request/response headers as span attributes:
os.environ["OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST"] = ".*"
os.environ["OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_RESPONSE"] = ".*"

###########################################
#   Context Instrumentation
###########################################


def wrap__load_runtime_context(wrapped, instance, args, kwargs):
    application = application_instance(activate=False)
    settings = global_settings() if not application else application.settings
    if not settings.opentelemetry.enabled:
        return wrapped(*args, **kwargs)

    from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext

    context = ContextVarsRuntimeContext()
    return context


def wrap_get_global_response_propagator(wrapped, instance, args, kwargs):
    application = application_instance(activate=False)
    settings = global_settings() if not application else application.settings
    if not settings.opentelemetry.enabled:
        return wrapped(*args, **kwargs)

    from opentelemetry.instrumentation.propagators import set_global_response_propagator

    from newrelic.api.opentelemetry import otel_context_propagator

    set_global_response_propagator(otel_context_propagator)

    return otel_context_propagator


def instrument_context_api(module):
    if hasattr(module, "_load_runtime_context"):
        wrap_function_wrapper(module, "_load_runtime_context", wrap__load_runtime_context)


def instrument_global_propagators_api(module):
    if hasattr(module, "get_global_response_propagator"):
        wrap_function_wrapper(module, "get_global_response_propagator", wrap_get_global_response_propagator)


###########################################
#   Trace Instrumentation
###########################################


def wrap_set_tracer_provider(wrapped, instance, args, kwargs):
    # This needs to act as a singleton, like the agent instance.
    # We should initialize the agent here as well, if there is
    # not an instance already.

    application = application_instance()
    if not application.active:
        # Force application registration if not already active
        application.activate()

    settings = global_settings() if not application else application.settings
    if not settings:
        # The application may need more time to start up
        time.sleep(0.5)
        settings = global_settings() if not application else application.settings
    if not settings or not settings.opentelemetry.enabled:
        return wrapped(*args, **kwargs)

    from newrelic.api.opentelemetry import TracerProvider

    global _TRACER_PROVIDER

    _TRACER_PROVIDER = TracerProvider()


def wrap_get_tracer_provider(wrapped, instance, args, kwargs):
    # This needs to act as a singleton, like the agent instance.
    # We should initialize the agent here as well, if there is
    # not an instance already.

    application = application_instance()
    if not application.active:
        # Force application registration if not already active
        application.activate()

    settings = global_settings() if not application else application.settings

    if not settings:
        # The application may need more time to start up
        time.sleep(0.5)
        settings = global_settings() if not application else application.settings

    if not settings or not settings.opentelemetry.enabled:
        return wrapped(*args, **kwargs)

    if not settings.opentelemetry.enabled:
        return wrapped(*args, **kwargs)

    from newrelic.api.opentelemetry import TracerProvider

    global _TRACER_PROVIDER

    _TRACER_PROVIDER = TracerProvider()
    return _TRACER_PROVIDER


def wrap_get_current_span(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    trace = current_trace()
    span = wrapped(*args, **kwargs)

    if not transaction:
        return span

    # Do not allow the wrapper to continue if
    # the Hybrid Agent setting is not enabled
    application = application_instance(activate=False)
    settings = global_settings() if not application else application.settings

    if not settings.opentelemetry.enabled:
        return span

    # If a NR trace does exist, check to see if the current
    # OTel span corresponds to the current NR trace.  If so,
    # return the original function's result.
    if span.get_span_context().span_id == int(trace.guid, 16):
        return span

    # If the current OTel span does not match the current NR
    # trace, this means that a NR trace was created either
    # manually or through the NR agent.  Either way, the OTel
    # API was not used to create a span object.  The Hybrid
    # Agent's Span object creates a NR trace but since the NR
    # trace has already been created, we just need a symbolic
    # OTel span to represent it the span object.  A LazySpan
    # will be created.  It will effectively be a NonRecordingSpan
    # with the ability to add custom attributes.

    from opentelemetry import trace as otel_api_trace

    from newrelic.api.opentelemetry import Span as HybridSpan

    class LazySpan(otel_api_trace.NonRecordingSpan, HybridSpan):
        def __init__(self, context):
            super().__init__(context)
            self.nr_trace = trace

        def set_attribute(self, key, value):
            add_custom_span_attribute(key, value)

        def set_attributes(self, attributes):
            for key, value in attributes.items():
                add_custom_span_attribute(key, value)

        def add_event(self, name, attributes=None, timestamp=None):
            return HybridSpan.add_event(self, name, attributes, timestamp)

        def add_link(self, span_context, attributes=None):
            return HybridSpan.add_link(self, span_context, attributes)

    span_context = otel_api_trace.SpanContext(
        trace_id=int(transaction.trace_id, 16),
        span_id=int(trace.guid, 16),
        is_remote=span.get_span_context().is_remote,
        trace_flags=otel_api_trace.TraceFlags(0x01),
        trace_state=otel_api_trace.TraceState(),
    )

    return LazySpan(span_context)


def wrap_start_internal_or_server_span(wrapped, instance, args, kwargs):
    # We want to take the NR version of the context_carrier
    # and put that into the attributes.  Keep the original
    # context_carrier intact.

    # Do not allow the wrapper to continue if
    # the Hybrid Agent setting is not enabled
    application = application_instance(activate=False)
    settings = global_settings() if not application else application.settings

    if not settings.opentelemetry.enabled:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)
    context_carrier = bound_args.get("context_carrier")
    attributes = bound_args.get("attributes", {})

    if context_carrier:
        if ("HTTP_HOST" in context_carrier) or ("http_version" in context_carrier):
            # This is an HTTP request (WSGI, ASGI, or otherwise)
            if "wsgi.version" in context_carrier:
                attributes["nr.wsgi.environ"] = context_carrier
            elif "asgi" in context_carrier:
                attributes["nr.asgi.scope"] = context_carrier
            else:
                attributes["nr.http.headers"] = context_carrier
        else:
            attributes["nr.nonhttp.headers"] = context_carrier

        bound_args["attributes"] = attributes

    return wrapped(**bound_args)


def wrap__get_span(wrapped, instance, args, kwargs):
    # Do not allow the wrapper to continue if
    # the Hybrid Agent setting is not enabled
    application = application_instance(activate=False)
    settings = global_settings() if not application else application.settings

    if not settings.opentelemetry.enabled:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)
    channel = bound_args.get("channel")
    properties = bound_args.get("properties")
    span_kind = bound_args.get("span_kind")
    task_name = bound_args.get("task_name")
    tracer = bound_args.get("tracer")

    properties_to_extract = ("correlation_id", "reply_to", "headers")

    if span_kind == span_kind.PRODUCER:
        # Do nothing special for producer spans
        pass
    elif channel:
        # This is a callback related consumer call
        # if transaction already exists, create trace
        # for callback; else, do not do anything
        tracer._create_consumer_trace = True
    elif not channel:
        # This is a consumer generator call
        # Create a new transaction only.
        # if transaction already exists, a new one
        # will not be created and nothing will occur.
        # This is the current behavior that Kafka has
        tracer._create_consumer_trace = False

    params = {"task_name": task_name}
    for _property in properties_to_extract:
        value = getattr(properties, _property, None)
        if properties and value:
            params[_property] = value
    span = wrapped(*args, **kwargs)
    span.set_attributes(params)

    return span


def instrument_trace_api(module):
    if hasattr(module, "set_tracer_provider"):
        wrap_function_wrapper(module, "set_tracer_provider", wrap_set_tracer_provider)

    if hasattr(module, "get_tracer_provider"):
        wrap_function_wrapper(module, "get_tracer_provider", wrap_get_tracer_provider)

    if hasattr(module, "get_current_span"):
        wrap_function_wrapper(module, "get_current_span", wrap_get_current_span)


def instrument_utils(module):
    if hasattr(module, "_start_internal_or_server_span"):
        wrap_function_wrapper(module, "_start_internal_or_server_span", wrap_start_internal_or_server_span)


def instrument_pika_utils(module):
    if hasattr(module, "_get_span"):
        wrap_function_wrapper(module, "_get_span", wrap__get_span)
