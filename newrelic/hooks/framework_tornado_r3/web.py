import logging
import traceback
import sys

from newrelic.agent import (callable_name, function_wrapper,
        wrap_function_wrapper, FunctionTrace, FunctionTraceWrapper)
from .util import (retrieve_request_transaction, record_exception,
        replace_current_transaction)

_logger = logging.getLogger(__name__)

def _find_defined_class(meth):
    # Returns the name of the class where the bound function method 'meth'
    # is implemented.
    mro = meth.__self__.__class__.__mro__
    for cls in mro:
        if meth.__name__ in cls.__dict__:
            return cls.__name__
    return None

class transaction_context(object):
    def __init__(self, transaction):
        self.transaction = transaction

    def __enter__(self):
        self.old_transaction = replace_current_transaction(self.transaction)

    def __exit__(self, exc_type, exc_value, traceback):
        replace_current_transaction(self.old_transaction)

@function_wrapper
def _requesthandler_method_wrapper(wrapped, instance, args, kwargs):
    request = instance.request
    transaction = retrieve_request_transaction(request)
    name = callable_name(wrapped)
    with transaction_context(transaction):
        with FunctionTrace(transaction, name=name):
            return wrapped(*args, **kwargs)

def _nr_wrapper_RequestHandler__execute_(wrapped, instance, args, kwargs):
    handler = instance
    request = handler.request

    if request is None:
        _logger.error('Runtime instrumentation error. Calling _execute on '
                'a RequestHandler when no request is present. Please '
                'report this issue to New Relic support.\n%s',
                ''.join(traceback.format_stack()[:-1]))
        return wrapped(*args, **kwargs)

    transaction = retrieve_request_transaction(request)

    if transaction is None:
        _logger.error('Runtime instrumentation error. Calling _execute on '
                'a RequestHandler when no transaction is present. Please '
                'report this issue to New Relic support.\n%s',
                ''.join(traceback.format_stack()[:-1]))
        return wrapped(*args, **kwargs)

    if request.method not in handler.SUPPORTED_METHODS:
        # If the method isn't one of the supported ones, then we expect the
        # wrapped method to raise an exception for HTTPError(405). In this case
        # we name the transaction after the wrapped method.
        name = callable_name(wrapped)
    else:
        # Otherwise we name the transaction after the handler function that
        # should end up being executed for the request.
        name = callable_name(getattr(handler, request.method.lower()))

    transaction.set_transaction_name(name)

    # We need to set the current transaction so that the user code executed by
    # running _execute is traced to the transaction we grabbed off the request

    with transaction_context(transaction):
      return wrapped(*args, **kwargs)


def _nr_wrapper_RequestHandler__handle_request_exception_(wrapped, instance,
        args, kwargs):

    # sys.exc_info() will have the correct exception context.
    # _handle_request_exception is private to tornado's web.py and also uses
    # sys.exc_info. The exception context has explicitly set the type, value,
    # and traceback.
    record_exception(sys.exc_info())
    return wrapped(*args, **kwargs)

def _nr_wrapper_RequestHandler__init__(wrapped, instance, args, kwargs):

    methods = ['head', 'get', 'post', 'delete', 'patch', 'put', 'options']

    for method in methods:
        func = getattr(instance, method, None)
        if func is not None:
            wrapped_func = FunctionTraceWrapper(func)
            setattr(instance, method, wrapped_func)

    # Only instrument prepare or on_finish if it has been re-implemented by
    # the user, the stubs on RequestHandler are meaningless noise.

    if _find_defined_class(instance.prepare) != 'RequestHandler':
        instance.prepare = FunctionTraceWrapper(instance.prepare)

    if _find_defined_class(instance.on_finish) != 'RequestHandler':
        instance.on_finish = FunctionTraceWrapper(instance.on_finish)

    if _find_defined_class(instance.data_received) != 'RequestHandler':
        instance.data_received =  _requesthandler_method_wrapper(
                instance.data_received)

    return wrapped(*args, **kwargs)

def instrument_tornado_web(module):
    wrap_function_wrapper(module, 'RequestHandler._execute',
            _nr_wrapper_RequestHandler__execute_)
    wrap_function_wrapper(module, 'RequestHandler._handle_request_exception',
            _nr_wrapper_RequestHandler__handle_request_exception_)
    wrap_function_wrapper(module, 'RequestHandler.__init__',
            _nr_wrapper_RequestHandler__init__)
