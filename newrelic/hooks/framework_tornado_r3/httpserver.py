import logging
import traceback

from newrelic.agent import wrap_function_wrapper
from .util import possibly_finalize_transaction

_logger = logging.getLogger(__name__)

# For every request either finish() or on_connection_close() is called on the
# _ServerRequestAdapter. We require that one of these methods is called before
# the transaction is allowed to be finalized.

def _transaction_can_finalize(wrapped, instance, args, kwargs):
    assert instance is not None

    if instance.delegate is not None:
        request = instance.delegate.request
    else:
        request = instance.request

    if request is None:
        _logger.error('Runtime instrumentation error. Ending request '
                'monitoring on ServerRequestAdapter when no request is '
                'present. Please report this issue to New Relic support.\n%s',
                ''.join(traceback.format_stack()[:-1]))
        return wrapped(*args, **kwargs)

    # We grab the transaction off of the request.
    if not hasattr(request, '_nr_transaction'):
        return wrapped(*args, **kwargs)

    if request._nr_transaction is None:
        return wrapped(*args, **kwargs)

    transaction = request._nr_transaction

    try:
        return wrapped(*args, **kwargs)
    finally:
        transaction._can_finalize = True

        # If finish() has been called, then request._finish_time will
        # be set and it should be used as transaction.last_byte_time.

        if request._finish_time:
            transaction.last_byte_time = request._finish_time

        possibly_finalize_transaction(transaction)

def _nr_wrapper__ServerRequestAdapter_on_connection_close_(wrapped, instance,
        args, kwargs):
    return _transaction_can_finalize(wrapped, instance, args, kwargs)

def _nr_wrapper__ServerRequestAdapter_finish_(wrapped, instance,
        args, kwargs):
    return _transaction_can_finalize(wrapped, instance, args, kwargs)

def instrument_tornado_httpserver(module):

    wrap_function_wrapper(module, '_ServerRequestAdapter.on_connection_close',
            _nr_wrapper__ServerRequestAdapter_on_connection_close_)
    wrap_function_wrapper(module, '_ServerRequestAdapter.finish',
            _nr_wrapper__ServerRequestAdapter_finish_)
