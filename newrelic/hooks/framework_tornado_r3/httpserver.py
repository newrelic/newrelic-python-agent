import logging
import traceback

from newrelic.agent import wrap_function_wrapper
from .util import (possibly_finalize_transaction,
        server_request_adapter_finish_finalize,
        server_request_adapter_on_connection_close_finalize)

_logger = logging.getLogger(__name__)

# For every request either finish() or on_connection_close() is called on the
# _ServerRequestAdapter. We require that one of these methods is called before
# the transaction is allowed to be finalized.

def _nr_wrapper__ServerRequestAdapter_on_connection_close_(wrapped, instance,
        args, kwargs):
    return server_request_adapter_on_connection_close_finalize(wrapped,
            instance, args, kwargs)

def _nr_wrapper__ServerRequestAdapter_finish_(wrapped, instance,
        args, kwargs):
    return server_request_adapter_finish_finalize(wrapped, instance, args,
            kwargs)

def instrument_tornado_httpserver(module):

    wrap_function_wrapper(module, '_ServerRequestAdapter.on_connection_close',
            _nr_wrapper__ServerRequestAdapter_on_connection_close_)
    wrap_function_wrapper(module, '_ServerRequestAdapter.finish',
            _nr_wrapper__ServerRequestAdapter_finish_)
