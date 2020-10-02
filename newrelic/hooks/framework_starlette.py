from newrelic.api.asgi_application import wrap_asgi_application
from newrelic.api.time_trace import current_trace
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper, function_wrapper
from newrelic.core.trace_cache import trace_cache


def framework_details():
    import starlette

    return ("Starlette", getattr(starlette, "__version__", None))


def bind_request(request, *args, **kwargs):
    return request


@function_wrapper
def route_naming_wrapper(wrapped, instance, args, kwargs):
    trace = getattr(bind_request(*args, **kwargs), "_nr_trace", None)
    transaction = trace and trace.transaction
    if transaction:
        transaction.set_transaction_name(callable_name(wrapped))

    force_propagate = current_trace() != trace

    # Propagate trace context onto the current task
    if force_propagate:
        thread_id = trace_cache().thread_start(trace)

    result = wrapped(*args, **kwargs)

    # Remove any context from the current thread as it was force propagated above
    if force_propagate:
        trace_cache().thread_stop(thread_id)

    return result


def bind_endpoint(path, endpoint, *args, **kwargs):
    return path, endpoint, args, kwargs


def wrap_route(wrapped, instance, args, kwargs):
    path, endpoint, args, kwargs = bind_endpoint(*args, **kwargs)
    endpoint = route_naming_wrapper(endpoint)

    return wrapped(path, endpoint, *args, **kwargs)


def wrap_request(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    result._nr_trace = current_trace()

    return result


def instrument_starlette_applications(module):
    wrap_asgi_application(module, "Starlette.__call__", framework=framework_details())


def instrument_starlette_routing(module):
    wrap_function_wrapper(module, "Route", wrap_route)


def instrument_starlette_requests(module):
    wrap_function_wrapper(module, "Request", wrap_request)
