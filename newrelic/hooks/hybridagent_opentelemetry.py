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

import time
import os
from pathlib import Path
from pprint import pprint

from newrelic.api.application import application_instance
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.common.agent_http import BaseClient
from newrelic.common.encoding_utils import base64_encode, obfuscate_license_key
from newrelic.core.config import global_settings

###########################################
#   Context Instrumentation
###########################################


def wrap__load_runtime_context(wrapped, instance, args, kwargs):
    application = application_instance(activate=False)
    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.traces.enabled):
        return wrapped(*args, **kwargs)

    from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext

    context = ContextVarsRuntimeContext()
    return context


def wrap_get_global_response_propagator(wrapped, instance, args, kwargs):
    from newrelic.api.opentelemetry import opentelemetry_context_propagator

    application = application_instance()
    if not application.active:
        # Force application registration if not already active
        application.activate()

    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.traces.enabled):
        return wrapped(*args, **kwargs)

    from opentelemetry.instrumentation.propagators import set_global_response_propagator

    set_global_response_propagator(opentelemetry_context_propagator)

    return opentelemetry_context_propagator


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

    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.traces.enabled):
        return wrapped(*args, **kwargs)

    nr_tracer_provider = application._agent.opentelemetry_tracer_provider(settings)
    return wrapped(nr_tracer_provider)


def wrap_get_tracer_provider(wrapped, instance, args, kwargs):
    # This needs to act as a singleton, like the agent instance.
    # We should initialize the agent here as well, if there is
    # not an instance already.

    application = application_instance()
    if not application.active:
        # Force application registration if not already active
        application.activate()

    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.traces.enabled):
        return wrapped(*args, **kwargs)

    return application._agent.opentelemetry_tracer_provider(settings)


def wrap_get_custom_headers(wrapped, instance, args, kwargs):
    # Capture all headers now and let New Relic handle
    # filtering, either through attribute filtering or
    # settings like HSM.

    capture_header_env_vars = [
        "OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_RESPONSE",
        "OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_CLIENT_RESPONSE",
    ]

    bound_args = bind_args(wrapped, args, kwargs)
    env_var = bound_args.get("env_var")
    if env_var and (env_var in capture_header_env_vars):
        return [".*"]

    return wrapped(*args, **kwargs)


def wrap_get_current_span(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    trace = current_trace()
    span = wrapped(*args, **kwargs)

    if not transaction:
        return span

    # Do not allow the wrapper to continue if
    # the Hybrid Agent setting is not enabled
    application = application_instance(activate=False)
    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.traces.enabled):
        return span

    # If a NR trace does exist, check to see if the current
    # OpenTelemetry span corresponds to the current NR trace.  If so,
    # return the original function's result.
    if span.get_span_context().span_id == int(trace.guid, 16):
        return span

    # If the current OpenTelemetry span does not match the current NR
    # trace, this means that a NR trace was created either
    # manually or through the NR agent.  Either way, the OpenTelemetry
    # API was not used to create a span object.  The Hybrid
    # Agent's Span object creates a NR trace but since the NR
    # trace has already been created, we just need a symbolic
    # OpenTelemetry span to represent it the span object.  A LazySpan
    # will be created.  It will effectively be a NonRecordingSpan
    # with the ability to add custom attributes.

    from opentelemetry import trace as otel_api_trace

    from newrelic.api.opentelemetry import LazySpan

    span_context = otel_api_trace.SpanContext(
        trace_id=int(transaction.trace_id, 16),
        span_id=int(trace.guid, 16),
        is_remote=span.get_span_context().is_remote,
        trace_flags=otel_api_trace.TraceFlags(0x01),
        trace_state=otel_api_trace.TraceState(),
    )

    return LazySpan(span_context, trace)


def wrap_start_internal_or_server_span(wrapped, instance, args, kwargs):
    # We want to take the NR version of the context_carrier
    # and put that into the attributes.  Keep the original
    # context_carrier intact.

    # Do not allow the wrapper to continue if
    # the Hybrid Agent setting is not enabled
    application = application_instance(activate=False)
    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.traces.enabled):
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
    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.traces.enabled):
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


def instrument_util_http(module):
    wrap_function_wrapper(module, "get_custom_headers", wrap_get_custom_headers)


###########################################
#   Meter Instrumentation
###########################################


def _subscribe_meter_provider(settings, meter_provider):
    """
    Accounts for a scenario where the meter_provider may have been
    set up but outside of the scope of New Relic's instrumentation.
    """
    if not (hasattr(meter_provider, "_update_resource") and hasattr(meter_provider, "add_metric_reader")):
        # If get_meter_provider() is called before set_meter_provider(),
        # a proxy MeterProvider will be passed in, so we need to exit early.
        return

    # Exit early if the meter provider already has an `entity.guid` set,
    # since this means it is already configured with a New Relic resource.
    try:
        guid = meter_provider._sdk_config.resource.attributes["entity.guid"]
        if guid:
            return
    except (AttributeError, KeyError):
        # Continue if the attribute is not present
        pass

    application = application_instance()
    if not application.active:
        # Force application registration if not already active
        application.activate()

    from newrelic.api.opentelemetry import meter_provider_resource_and_reader_generator
    nr_resource, nr_reader = meter_provider_resource_and_reader_generator(settings)

    meter_provider._update_resource(nr_resource)

    # add_metric_reader() only wires nr_reader into live measurement routing;
    # it does not add it to _metric_readers, which is the list that
    # MeterProvider.shutdown()/force_flush() actually iterate to flush a
    # reader's buffered data.  Without this, nr_reader would only ever export
    # via its own periodic background thread, and anything it buffered would
    # be silently dropped if the process exits before that interval elapses.
    meter_provider.add_metric_reader(nr_reader)
    meter_provider._metric_readers = list(meter_provider._metric_readers) + [nr_reader]

    if not application._agent._meter_provider:
        application._agent._meter_provider = meter_provider


def wrap_MeterProvider(wrapped, instance, args, kwargs):
    # We should initialize the agent here as well, if there is
    # not an instance already.
    application = application_instance()
    if not application.active:
        # Force application registration if not already active
        application.activate()

    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.metrics.enabled):
        return wrapped(*args, **kwargs)

    # Logic to avoid adding duplicate NR metric readers to the MeterProvider
    try:
        guid = instance._sdk_config.resource.attributes["entity.guid"]
        if guid:
            return wrapped(*args, **kwargs)
    except (AttributeError, KeyError):
        pass

    from newrelic.api.opentelemetry import meter_provider_resource_and_reader_generator
    nr_resource, nr_reader = meter_provider_resource_and_reader_generator(settings)

    # Before we run __init__ we need to add our metric reader to arg BEFORE running __init__
    bound_args = bind_args(wrapped, args, kwargs)
    metric_readers = bound_args.get("metric_readers", [])
    nr_reader = [nr_reader]
    nr_reader.extend(metric_readers)
    bound_args["metric_readers"] = nr_reader

    result = wrapped(**bound_args)

    # resource attributes can be done after the MeterProvider is initialized
    instance._update_resource(nr_resource)

    if application._agent._meter_provider is None:
        application._agent._meter_provider = instance

    return result


def wrap_set_meter_provider(wrapped, instance, args, kwargs):
    # This needs to act as a singleton, like the agent instance.
    # We should initialize the agent here as well, if there is
    # not an instance already.

    application = application_instance()
    if not application.active:
        # Force application registration if not already active
        application.activate()

    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.metrics.enabled):
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)
    meter_provider = bound_args.get("meter_provider")

    if meter_provider is not None:
        _subscribe_meter_provider(settings, meter_provider)

    return wrapped(*args, **kwargs)


def wrap_get_meter_provider(wrapped, instance, args, kwargs):
    # This needs to act as a singleton, like the agent instance.
    # We should initialize the agent here as well, if there is
    # not an instance already.

    application = application_instance()
    if not application.active:
        # Force application registration if not already active
        application.activate()

    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.metrics.enabled):
        return wrapped(*args, **kwargs)

    meter_provider = wrapped(*args, **kwargs)
    if meter_provider and (application._agent._meter_provider is None):
        # Accounts for a scenario where the meter_provider may have been
        # set up but outside of the scope of New Relic's instrumentation.
        _subscribe_meter_provider(settings, meter_provider)

    return meter_provider


def instrument_MeterProvider(module):
    if hasattr(module, "MeterProvider"):
        wrap_function_wrapper(module, "MeterProvider.__init__", wrap_MeterProvider)


def wrap_requests_transport_request(wrapped, instance, args, kwargs):
    application = application_instance()
    settings = getattr(application, "settings", None) or global_settings()

    if settings and not (settings.opentelemetry.enabled and settings.opentelemetry.metrics.enabled) or (settings and not settings.audit_log_file):
        return wrapped(*args, **kwargs)

    # Manually print the required information to the audit log.
    # This done primarily due to the fact that there is slightly different
    # information being processed by the HTTPClient Session's `log_request`
    # and `log_response` methods compared to what is needed in the audit
    # log.  To keep the formatting consistent, the audit log ID is manually
    # incremented and retrieved for each request.

    try:
        application._agent._applications[application.name]._active_session.CLIENT.AUDIT_LOG_ID += 1
        audit_log_id = application._agent._applications[application.name]._active_session.CLIENT.AUDIT_LOG_ID
    except Exception:
        audit_log_id = None

    audit_log_file = Path(settings.audit_log_file).open("a")
    
    bound_args = bind_args(wrapped, args, kwargs)
    url = bound_args.get("url")
    request_headers = bound_args.get("headers")
    request_body = bound_args.get("data")
    request_byte_count = len(request_body) if request_body else 0

    if request_headers:
        request_headers = {
            k: obfuscate_license_key(v) if k.lower() == "api-key" else v
            for k, v in request_headers.items()
        }

    print(f"TIME: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())!r}", file=audit_log_file)
    print(file=audit_log_file)

    if audit_log_id:
        print(f"ID: {audit_log_id!r}", file=audit_log_file)
        print(file=audit_log_file)
    
    print(f"PID: {os.getpid()!r}", file=audit_log_file)
    print(file=audit_log_file)
    print(f"URL: {url!r}", file=audit_log_file)
    print(file=audit_log_file)
    print("HEADERS:", end=" ", file=audit_log_file)
    pprint(dict(request_headers), stream=audit_log_file)
    print(file=audit_log_file)
    print(f"BYTE COUNT: {request_byte_count!r}", file=audit_log_file)
    print(file=audit_log_file)
    print(f"DATA: {base64_encode(request_body)}", file=audit_log_file)
    print(file=audit_log_file)
    print(78 * "=", file=audit_log_file)
    print(file=audit_log_file)

    result = wrapped(*args, **kwargs)

    response_body = result.content()
    response_status_code = result.status_code
    response_headers = result.headers()
    response_byte_count = len(response_body) if response_body else 0

    print(f"TIME: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())!r}", file=audit_log_file)
    print(file=audit_log_file)

    if audit_log_id:
        print(f"ID: {audit_log_id!r}", file=audit_log_file)
        print(file=audit_log_file)

    print(f"PID: {os.getpid()!r}", file=audit_log_file)
    print(file=audit_log_file)
    print(f"STATUS: {response_status_code!r}", file=audit_log_file)
    print(file=audit_log_file)
    print("HEADERS:", end=" ", file=audit_log_file)
    pprint(dict(response_headers), stream=audit_log_file)
    print(file=audit_log_file)
    print(f"BYTE COUNT: {response_byte_count!r}", file=audit_log_file)
    print(file=audit_log_file)
    print(f"RESULT: [{base64_encode(response_body)}]", file=audit_log_file)
    print(file=audit_log_file)
    print(78 * "=", file=audit_log_file)
    print(file=audit_log_file)

    audit_log_file.flush()
    return result


def instrument_meter_api(module):
    if hasattr(module, "set_meter_provider"):
        wrap_function_wrapper(module, "set_meter_provider", wrap_set_meter_provider)

    if hasattr(module, "get_meter_provider"):
        wrap_function_wrapper(module, "get_meter_provider", wrap_get_meter_provider)


def instrument_requests_transport(module):
    if hasattr(module, "RequestsHTTPTransport") and hasattr(module.RequestsHTTPTransport, "request"):
        wrap_function_wrapper(module, "RequestsHTTPTransport.request", wrap_requests_transport_request)