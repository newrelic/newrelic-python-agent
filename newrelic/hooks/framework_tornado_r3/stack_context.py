import sys

from newrelic.agent import function_wrapper, wrap_function_wrapper
from six.moves import range
from .util import (create_transaction_aware_fxn, record_exception,
        retrieve_current_transaction)

def _nr_wrapper_stack_context_wrap_(wrapped, instance, args, kwargs):
    # Lots of wrapping going on here. There's the original function, and
    # then 2 layers of wrapping around it.
    #
    # unwrapped_fxn (unwrapped original):
    #     The original function passed into `stack_context.wrap()`.
    #
    # wrapped_fxn (wrapped by Tornado):
    #    The resulting function after `unwrapped_fxn` has been wrapped by
    #    `stack_context.wrap()`.
    #
    # transaction_aware_fxn (wrapped by NR agent):
    #    The resulting function after our `create_transaction_aware_fxn()`
    #    has wrapped `wrapped_fxn` and associated it with the current
    #    transaction.

    def _fxn_arg_extractor(fn, *args, **kwargs):
        # fn is the name of the callable argument in stack_context.wrap
        return fn

    unwrapped_fxn = _fxn_arg_extractor(*args, **kwargs)
    wrapped_fxn = wrapped(*args, **kwargs)

    transaction_aware_fxn = create_transaction_aware_fxn(wrapped_fxn,
            unwrapped_fxn)

    if transaction_aware_fxn is None:
        return wrapped_fxn

    # To prevent stack_context.wrap from re-wrapping this function we attach
    # Tornado's attribute indicating the function was wrapped here.
    transaction_aware_fxn._wrapped = True

    # To prevent us from re-wrapping and to associate the transaction with the
    # function, we attach the transaction as an attribute.
    transaction_aware_fxn._nr_transaction = retrieve_current_transaction()

    return transaction_aware_fxn

# When an exception occurs in a stack context wrapped function,
# _handle_exception is called. We wrap it to record the exception.
def _nr_wrapper_handle_exception_(wrapped, instance, args, kwargs):

    # Pull out the passed in exception. In python 2.7 and pypy this matches
    # sys.exc_info(). However, in python 3 sys.exc_info() can return
    # (None, None, None) in some contexts.

    def _exc_extractor(tail, exc, *args, **kwargs):
        return exc

    exc = _exc_extractor(*args, **kwargs)

    record_exception(exc)
    return wrapped(*args, **kwargs)

def instrument_tornado_stack_context(module):
    wrap_function_wrapper(module, 'wrap', _nr_wrapper_stack_context_wrap_)
    wrap_function_wrapper(module, '_handle_exception',
            _nr_wrapper_handle_exception_)
