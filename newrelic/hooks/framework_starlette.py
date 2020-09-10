from newrelic.api.asgi_application import wrap_asgi_application
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper, function_wrapper


def framework_details():
    import starlette

    return ("Starlette", getattr(starlette, "__version__", None))


@function_wrapper
def route_naming_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction:
        transaction.set_transaction_name(callable_name(wrapped))

    return wrapped(*args, **kwargs)


def bind_endpoint(path, endpoint, *args, **kwargs):
    return path, endpoint, args, kwargs


def wrap_route(wrapped, instance, args, kwargs):
    path, endpoint, args, kwargs = bind_endpoint(*args, **kwargs)
    endpoint = route_naming_wrapper(endpoint)
    return wrapped(path, endpoint, *args, **kwargs)


def instrument_starlette_applications(module):
    wrap_asgi_application(module, "Starlette.__call__", framework=framework_details())


def instrument_starlette_routing(module):
    wrap_function_wrapper(module, "Route", wrap_route)
