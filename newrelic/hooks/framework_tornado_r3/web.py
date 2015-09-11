import logging
import traceback

from newrelic.agent import callable_name, wrap_function_wrapper
from .util import retrieve_request_transaction

_logger = logging.getLogger(__name__)

def _nr_wrapper_RequestHandler_on_finish_(wrapped, instance, args, kwargs):

    assert instance is not None

    request = instance.request

    if request is None:
        _logger.error('Runtime instrumentation error. Calling on_finish on '
                'a RequestHandler when no request is present. Please '
                'report this issue to New Relic support.\n%s',
                ''.join(traceback.format_stack()[:-1]))
        return wrapped(*args, **kwargs)

    transaction = retrieve_request_transaction(request)

    if transaction is None:
        _logger.error('Runtime instrumentation error. Calling on_finish on '
                'a RequestHandler when no transaction is present. Please '
                'report this issue to New Relic support.\n%s',
                ''.join(traceback.format_stack()[:-1]))
        return wrapped(*args, **kwargs)

    transaction._is_request_finished = True

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

    return wrapped(*args, **kwargs)

def instrument_tornado_web(module):
    wrap_function_wrapper(module, 'RequestHandler.on_finish',
            _nr_wrapper_RequestHandler_on_finish_)
    wrap_function_wrapper(module, 'RequestHandler._execute',
            _nr_wrapper_RequestHandler__execute_)
