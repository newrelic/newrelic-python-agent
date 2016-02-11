import sys

from newrelic.agent import function_wrapper, wrap_function_wrapper
from six.moves import range
from .util import (create_transaction_aware_fxn, record_exception,
        retrieve_current_transaction, transaction_context)

def _nr_wrapper_stack_context_wrap_(wrapped, instance, args, kwargs):

    def _fxn_arg_extractor(fn, *args, **kwargs):
        # fn is the name of the callable argument in stack_context.wrap
        return fn

    fxn = _fxn_arg_extractor(*args, **kwargs)

    transaction_aware_fxn = create_transaction_aware_fxn(fxn)

    # If transaction_aware_fxn is None then it is already wrapped, or the fxn
    # is None.
    if transaction_aware_fxn is None:
        return wrapped(*args, **kwargs)

    transaction = retrieve_current_transaction()

    # We replace the function we call in the callback with the transaction aware
    # version of the function.
    if len(args) > 0:
        args = list(args)
        args[0] = transaction_aware_fxn
    else:
        # Keyword argument name for the callable function is 'fn'.
        kwargs['fn'] = transaction_aware_fxn

    try:
        stack_context_wrapped_fxn = wrapped(*args, **kwargs)
        # Since our context aware function is wrapped by the stack context
        # wrapper function we label the newly wrapped function with our
        # transaction to keep track of it.
        stack_context_wrapped_fxn._nr_transaction = transaction
        return stack_context_wrapped_fxn
    except:  # Catch all.
        record_exception(sys.exc_info())
        raise


# This allows us to capture all exceptions that get swallowed by the ioloop.
# If we instrument the exception handler directly this will cause us to call
# record exception twice. However, this is ok because we in
# transaction.record_exception we filter repeats.
def _nr_wrapper_ExceptionStackContext__init__(wrapped, instance, args, kwargs):

    assert instance is not None

    result = wrapped(*args, **kwargs)

    # instance is now an initiated ExceptionStackContext object.
    instance.exception_handler = _instrument_exception_handler(instance)

    return result

def _instrument_exception_handler(esc_instance):
    # We keep track of the transaction the ExceptionHandler was instantiated in.
    transaction = retrieve_current_transaction()

    @function_wrapper
    def _wrap_exception_handler(wrapped, instance, args, kwargs):

        def _bind_params(type, value, traceback, *args, **kwargs):
            return type, value, traceback

        type, value, traceback = _bind_params(*args, **kwargs)

        is_exception_swallowed = wrapped(*args, **kwargs)

        if is_exception_swallowed:
            with transaction_context(transaction):
                record_exception((type, value, traceback))

        return is_exception_swallowed

    return _wrap_exception_handler(esc_instance.exception_handler)

def instrument_tornado_stack_context(module):
    wrap_function_wrapper(module, 'wrap', _nr_wrapper_stack_context_wrap_)
    wrap_function_wrapper(module, 'ExceptionStackContext.__init__',
            _nr_wrapper_ExceptionStackContext__init__)
