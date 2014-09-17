import sys
import logging

from newrelic.agent import (wrap_function_wrapper, current_transaction,
        FunctionTrace, callable_name, FunctionWrapper)

from . import (retrieve_transaction_request, retrieve_request_transaction,
    request_finished, suspend_request_monitoring, resume_request_monitoring,
    finalize_request_monitoring, record_exception)

_logger = logging.getLogger(__name__)

module_stack_context = None

def callback_wrapper(request):

    def _callback_wrapper(wrapped, instance, args, kwargs):

        if current_transaction():
            return wrapped(*args, **kwargs)

        transaction = resume_request_monitoring(request)

        if transaction is None:
            return wrapped(*args, **kwargs)

        try:
            name = callable_name(wrapped)

            with FunctionTrace(transaction, name=name):
                return wrapped(*args, **kwargs)

        except Exception:
            record_exception(transaction, sys.exc_info())
            raise

        finally:
            if not request_finished(request):
                suspend_request_monitoring(request, name='Callback/Wait')

            elif not request.connection.stream.writing():
                finalize_request_monitoring(request)

            else:
                suspend_request_monitoring(request, name='Request/Output')

    return _callback_wrapper

def stack_context_wrap_wrapper(wrapped, instance, args, kwargs):
    def _args(fn, *args, **kwargs):
        return fn

    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    request = retrieve_transaction_request(transaction)

    if request is None:
        return wrapped(*args, **kwargs)

    fn = _args(*args, **kwargs)

    # Tornado 3.1 doesn't use _StackContextWrapper and checks
    # for a '_wrapped' attribute instead which makes this a
    # bit more fragile.

    if hasattr(module_stack_context, '_StackContextWrapper'):
        if fn is None or fn.__class__ is module_stack_context._StackContextWrapper:
            return fn
    else:
        if fn is None or hasattr(fn, '_wrapped'):
            return fn

    fn = FunctionWrapper(fn, callback_wrapper(request))

    return wrapped(fn)

def instrument_tornado_stack_context(module):
    global module_stack_context
    module_stack_context = module

    wrap_function_wrapper(module, 'wrap', stack_context_wrap_wrapper)
