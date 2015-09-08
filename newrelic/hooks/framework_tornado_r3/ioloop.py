import logging

from newrelic.agent import wrap_function_wrapper
from .util import finalize_transaction

_logger = logging.getLogger(__name__)

def _nr_wrapper_IOLoop__run_callback_(wrapped, instance, args, kwargs):
    # callback in wrapped in functools.partial so to get the actual callback
    # we need to grab the func attribute.
    # TODO(bdirks): asyncio and twisted override add_callback but should still
    # work. See tornado-4.2/tornado/platform/(asyncio|twisted).py. We should
    # explicitly test this.
    def _callback_extractor(callback, *args, **kwargs):
        try:
            return callback.func
        except:
            _logger.error('Runtime instrumentation error. A callback is '
                    'registered on the ioloop that isn\'t wrapped in '
                    'functools.partial. Perhaps a nonstandard IOLoop is being'
                    'used?')
            return None

    callback = _callback_extractor(*args, **kwargs)

    ret = wrapped(*args, **kwargs)

    # Finalize the callback if it is done.
    if hasattr(callback, '_nr_transaction'):
        transaction = callback._nr_transaction
        if transaction._is_request_finished and not transaction._is_finalized:
            finalize_transaction(callback._nr_transaction)
    return ret

def instrument_tornado_ioloop(module):
    wrap_function_wrapper(module, 'IOLoop._run_callback',
            _nr_wrapper_IOLoop__run_callback_)
