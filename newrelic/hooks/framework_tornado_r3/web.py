import logging

from newrelic.agent import wrap_function_wrapper
from . import retrieve_request_transaction

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

def instrument_tornado_web(module):
    wrap_function_wrapper(module, 'RequestHandler.on_finish',
            _nr_wrapper_RequestHandler_on_finish_)
