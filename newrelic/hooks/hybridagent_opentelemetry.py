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

from newrelic.api.application import application_instance
from newrelic.api.time_trace import add_custom_span_attribute, current_trace
from newrelic.api.transaction import Sentinel, current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)
_TRACER_PROVIDER = None

###########################################
#   Trace Instrumentation
###########################################


def wrap_set_tracer_provider(wrapped, instance, args, kwargs):
    settings = global_settings()

    if not settings.otel_bridge.enabled:
        return wrapped(*args, **kwargs)

    global _TRACER_PROVIDER

    if _TRACER_PROVIDER is None:
        bound_args = bind_args(wrapped, args, kwargs)
        tracer_provider = bound_args.get("tracer_provider")
        _TRACER_PROVIDER = tracer_provider
    else:
        _logger.warning("TracerProvider has already been set.")


def wrap_get_tracer_provider(wrapped, instance, args, kwargs):
    settings = global_settings()

    if not settings.otel_bridge.enabled:
        return wrapped(*args, **kwargs)

    # This needs to act as a singleton, like the agent instance.
    # We should initialize the agent here as well, if there is
    # not an instance already.
    application = application_instance(activate=False)
    if not application or (application and not application.active):
        application_instance().activate()

    global _TRACER_PROVIDER

    if _TRACER_PROVIDER is None:
        from newrelic.api.opentelemetry import TracerProvider
        
        hybrid_agent_tracer_provider = TracerProvider("hybrid_agent_tracer_provider")
        _TRACER_PROVIDER = hybrid_agent_tracer_provider
    return _TRACER_PROVIDER


def wrap_get_current_span(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    trace = current_trace()

    # If a NR trace does not exist (aside from the Sentinel
    # trace), return the original function's result.
    if not transaction or isinstance(trace, Sentinel):
        return wrapped(*args, **kwargs)

    # Do not allow the wrapper to continue if
    # the Hybrid Agent setting is not enabled
    settings = transaction.settings or global_settings()

    if not settings.otel_bridge.enabled:
        return wrapped(*args, **kwargs)

    # If a NR trace does exist, check to see if the current
    # OTel span corresponds to the current NR trace.  If so,
    # return the original function's result.
    span = wrapped(*args, **kwargs)

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

    class LazySpan(otel_api_trace.NonRecordingSpan):
        def set_attribute(self, key, value):
            add_custom_span_attribute(key, value)

        def set_attributes(self, attributes):
            for key, value in attributes.items():
                add_custom_span_attribute(key, value)

    otel_tracestate_headers = None

    span_context = otel_api_trace.SpanContext(
        trace_id=int(transaction.trace_id, 16),
        span_id=int(trace.guid, 16),
        is_remote=span.get_span_context().is_remote,
        trace_flags=otel_api_trace.TraceFlags(span.get_span_context().trace_flags),
        trace_state=otel_api_trace.TraceState(otel_tracestate_headers),
    )

    return LazySpan(span_context)


def wrap_start_internal_or_server_span(wrapped, instance, args, kwargs):
    # We want to take the NR version of the context_carrier
    # and put that into the attributes.  Keep the original
    # context_carrier intact.

    # Do not allow the wrapper to continue if
    # the Hybrid Agent setting is not enabled
    settings = global_settings()

    if not settings.otel_bridge.enabled:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)
    context_carrier = bound_args.get("context_carrier")
    attributes = bound_args.get("attributes", {})

    if context_carrier:
        if ("HTTP_HOST" in context_carrier) or ("http_version" in context_carrier):
            # This is an HTTP request (WSGI, ASGI, or otherwise)
            nr_environ = context_carrier.copy()
            attributes["nr.http.headers"] = nr_environ

        else:
            nr_headers = context_carrier.copy()
            attributes["nr.nonhttp.headers"] = nr_headers

        bound_args["attributes"] = attributes

    return wrapped(**bound_args)


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
