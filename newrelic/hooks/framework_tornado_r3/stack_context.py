import sys

from newrelic.agent import (wrap_function_wrapper, FunctionTrace,
    callable_name)
from six.moves import range
from . import (record_exception, retrieve_current_transaction,
               replace_current_transaction)

def _nr_wrapper_stack_context_wrap_(wrapped, instance, args, kwargs):

    def _fxn_arg_extractor(fn, *args, **kwargs):
        return fn

    return _stack_context_wrapper_helper(_fxn_arg_extractor, 0, 'fn', wrapped,
            instance, args, kwargs)

def _stack_context_wrapper_helper(fxn_arg_extractor, fxn_arg_index,
        fxn_arg_name, wrapped, instance, args, kwargs):

    fxn = fxn_arg_extractor(*args, **kwargs)

    if fxn is None:
        return wrapped(*args, **kwargs)

    transaction_aware_fxn = _create_transaction_aware_fxn(fxn, wrapped,
        instance, args, kwargs)

    # If transaction_aware_fxn is None then it is either not being called in
    # the context of a transaction or it is already wrapped.
    # Either way we do not need to wrap this function.
    if not transaction_aware_fxn:
        return wrapped(*args, **kwargs)

    transaction = retrieve_current_transaction()

    # We replace the function we call in the callback with the transaction aware
    # version of the function.
    if len(args) > fxn_arg_index:
        # args is a tuple so must make a copy instead of overwriting the
        # function at fxn_arg_index
        args = map(lambda i: args[i] if i != fxn_arg_index else
                transaction_aware_fxn, range(0, len(args)))
    else:
        kwargs[fxn_arg_name] = transaction_aware_fxn

    try:
        # TODO: investigate whether we care about instrumenting the wrapping.
        name = callable_name(wrapped)
        with FunctionTrace(transaction, name=name):
            stack_context_wrapped_fxn = wrapped(*args, **kwargs)
            # Since our context aware function is wrapped by the stack context
            # wrapper function we label the newly wrapped function with our
            # transaction to keep track of it.
            stack_context_wrapped_fxn._nr_transaction = transaction
            return stack_context_wrapped_fxn
    except:  # Catch all.
        record_exception(transaction, sys.exc_info())
        raise

def _create_transaction_aware_fxn(fxn, wrapped, instance, args, kwargs):
    # Returns a version of fxn that will switch context to the appropriate
    # transaction and then restore the previous transaction on exit.
    # If fxn is already transaction aware or if there is no transaction
    # associated with fxn, this will return None.

    # If fxn already has the stored transaction we don't want to rewrap it
    # since this is also cause Tornado's stack_context.wrap to rewrap it.
    # That Tornado method will also return the input fxn immediately if
    # previously wrapped.

    if hasattr(fxn, '_nr_transaction'):
        return None

    # We want to get the transaction associated with this path of execution
    # whether or not we are actively recording information about it.
    transaction = retrieve_current_transaction()

    # A transaction will be None for fxns scheduled on the ioloop not
    # associated with a transaction.
    if transaction is None:
        return None

    def _transaction_aware_fxn(*fxn_args, **fxn_kwargs):
        old_transaction = retrieve_current_transaction()
        replace_current_transaction(transaction)
        name = callable_name(fxn)
        with FunctionTrace(transaction, name=name):
            ret = fxn(*fxn_args, **fxn_kwargs)
        replace_current_transaction(old_transaction)
        return ret

    return _transaction_aware_fxn

def instrument_tornado_stack_context(module):
    wrap_function_wrapper(module, 'wrap', _nr_wrapper_stack_context_wrap_)
    wrap_function_wrapper(module, 'run_with_stack_context',
            _nr_wrapper_run_with_stack_context_)
