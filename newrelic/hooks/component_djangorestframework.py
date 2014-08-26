from newrelic.agent import (wrap_function_wrapper, current_transaction,
    FunctionTrace, callable_name, wrap_function_trace)

def _nr_wrapper_APIView_dispatch_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def _args(request, *args, **kwargs):
        return request

    view = instance
    request = _args(*args, **kwargs)

    if request.method.lower() in view.http_method_names:
        handler = getattr(view, request.method.lower(),
                          view.http_method_not_allowed)
    else:
        handler = view.http_method_not_allowed

    name = callable_name(handler)

    transaction.set_transaction_name(name)

    with FunctionTrace(transaction, name):
        return wrapped(*args, **kwargs)

def instrument_rest_framework_views(module):
    wrap_function_wrapper(module, 'APIView.dispatch',
            _nr_wrapper_APIView_dispatch_)
