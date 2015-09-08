import logging
import traceback

from newrelic.agent import wrap_function_wrapper
from . import finalize_request_monitoring

_logger = logging.getLogger(__name__)

# For every request either finish() or on_connection_close() is called on the
# _ServerRequestAdapter. If finish() is called we handle to end of the request
# in the request handler. Otherwise we handle it here.

def _nr_wrapper__ServerRequestAdapter_on_connection_close_(wrapped, instance,
        args, kwargs):

    assert instance is not None

    request = instance.connection._nr_current_request()
    if request is None:
        _logger.error('Runtime instrumentation error. Ending request '
                'monitoring on ServerRequestAdapter when no request is '
                'present. Please report this issue to New Relic support.\n%s',
                ''.join(traceback.format_stack()[:-1]))
        return wrapped(*args, **kwargs)

    result = wrapped(*args, **kwargs)
    finalize_request_monitoring(request)
    return result

def instrument_tornado_httpserver(module):
    wrap_function_wrapper(module, '_ServerRequestAdapter.on_connection_close',
            _nr_wrapper__ServerRequestAdapter_on_connection_close_)
