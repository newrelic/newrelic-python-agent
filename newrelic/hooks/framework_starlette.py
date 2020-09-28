from newrelic.api.asgi_application import wrap_asgi_application
from newrelic.api.background_task import BackgroundTaskWrapper
from newrelic.api.time_trace import current_trace
from newrelic.api.function_trace import FunctionTraceWrapper, wrap_function_trace
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper, function_wrapper
from newrelic.core.trace_cache import trace_cache
from newrelic.api.time_trace import record_exception
from newrelic.core.config import ignore_status_code


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

    force_propagate = trace and current_trace() is None

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


def bind_exception(request, exc, *args, **kwargs):
    return request, exc, args, kwargs


def wrap_route(wrapped, instance, args, kwargs):
    path, endpoint, args, kwargs = bind_endpoint(*args, **kwargs)
    endpoint = route_naming_wrapper(FunctionTraceWrapper(endpoint))
    return wrapped(path, endpoint, *args, **kwargs)


def wrap_request(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    instance._nr_trace = current_trace()

    return result


def wrap_background_method(wrapped, instance, args, kwargs):
    func = getattr(instance, "func", None)
    if func:
        instance.func = BackgroundTaskWrapper(func)
    return wrapped(*args, **kwargs)


@function_wrapper
def wrap_middleware(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    dispatch_func = getattr(result, "dispatch_func", None)
    name = dispatch_func and callable_name(dispatch_func)

    return FunctionTraceWrapper(result, name=name)


def bind_middleware(middleware_class, *args, **kwargs):
    return middleware_class, args, kwargs


def wrap_add_middleware(wrapped, instance, args, kwargs):
    middleware, args, kwargs = bind_middleware(*args, **kwargs)
    return wrapped(wrap_middleware(middleware), *args, **kwargs)


def bind_middleware_starlette(
    debug=False, routes=None, middleware=None, *args, **kwargs
):
    return middleware


def wrap_starlette(wrapped, instance, args, kwargs):
    middlewares = bind_middleware_starlette(*args, **kwargs)
    if middlewares:
        for middleware in middlewares:
            cls = getattr(middleware, "cls", None)
            if cls and not hasattr(cls, "__wrapped__"):
                middleware.cls = wrap_middleware(cls)

    return wrapped(*args, **kwargs)


def wrap_exception_middleware(wrapped, instance, args, kwargs):
    request, exc, args, kwargs = bind_exception(*args, **kwargs)
    if not ignore_status_code(exc.status_code):
        record_exception()
    return wrapped(request, exc, *args, **kwargs)


def instrument_starlette_applications(module):
    framework = framework_details()
    version_info = tuple(int(v) for v in framework[1].split(".", 3)[:3])

    wrap_asgi_application(module, "Starlette.__call__", framework=framework)
    wrap_function_wrapper(module, "Starlette.add_middleware", wrap_add_middleware)

    if version_info >= (0, 12, 13):
        wrap_function_wrapper(module, "Starlette.__init__", wrap_starlette)


def instrument_starlette_routing(module):
    wrap_function_wrapper(module, "Route.__init__", wrap_route)


def instrument_starlette_requests(module):
    wrap_function_wrapper(module, "Request.__init__", wrap_request)


def instrument_starlette_middleware_errors(module):
    wrap_function_trace(module, "ServerErrorMiddleware.__call__")


def instrument_starlette_exceptions(module):
    wrap_function_trace(module, "ExceptionMiddleware.__call__")

    wrap_function_wrapper(module, "ExceptionMiddleware.http_exception",
        wrap_exception_middleware)


def instrument_starlette_background_task(module):
    wrap_function_wrapper(module, "BackgroundTask.__call__", wrap_background_method)