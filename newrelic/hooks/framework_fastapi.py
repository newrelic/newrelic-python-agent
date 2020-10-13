from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.object_names import callable_name


def bind_dependant(dependant, *args, **kwargs):
    return dependant


def wrap_run_endpoint_function(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction:
        dependant = bind_dependant(*args, **kwargs)
        transaction.set_transaction_name(callable_name(dependant.call))
    return wrapped(*args, **kwargs)


def instrument_fastapi_routing(module):
    wrap_function_wrapper(module, "run_endpoint_function", wrap_run_endpoint_function)
