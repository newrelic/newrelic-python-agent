import sys

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.object_wrapper import ObjectWrapper, callable_name
from newrelic.api.transaction import current_transaction
from newrelic.api.pre_function import wrap_pre_function

def wrap_handle_exception(*args):
    transaction = current_transaction()
    if transaction:
        transaction.record_exception(*sys.exc_info())

def outer_fn_wrapper(outer_fn, instance, args, kwargs):
    view_name = args[0]
    view_fn = getattr(instance, view_name, None)
    name = view_fn and callable_name(view_fn)

    def inner_fn_wrapper(inner_fn, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None or name is None:
            return inner_fn(*args, **kwargs)

        transaction.name_transaction(name, priority=4)

        with FunctionTrace(transaction, name=name):
            try:
                return inner_fn(*args, **kwargs)
            except:
                transaction.record_exception(*sys.exc_info())

    result = outer_fn(*args, **kwargs)

    return ObjectWrapper(result, None, inner_fn_wrapper)

def instrument_tastypie_resources(module):
    _wrap_view = module.Resource.wrap_view
    module.Resource.wrap_view = ObjectWrapper(_wrap_view, None, outer_fn_wrapper)
    wrap_pre_function(module, 'Resource._handle_500', wrap_handle_exception)
