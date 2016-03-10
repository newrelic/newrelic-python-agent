import logging
import sys
import traceback

from newrelic.agent import wrap_function_wrapper
from .util import (possibly_finalize_transaction, record_exception,
        retrieve_current_transaction, current_thread_id)

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
    transaction = getattr(callback, '_nr_transaction', None)
    if transaction is not None:
        # Mark this callback as ran so calls to cancel timers know not to
        # decrement the callback ref count

        callback._nr_callback_ran = True


    ret = wrapped(*args, **kwargs)

    if transaction is not None:
        transaction._ref_count -= 1

        # Finalize the transaction if this is the last callback.
        possibly_finalize_transaction(callback._nr_transaction)

    return ret

def _nr_wrapper_IOLoop_handle_callback_exception_(
        wrapped, instance, args, kwargs):

    def _callback_extractor(callback, *args, **kwargs):
        return callback

    cb = _callback_extractor(*args, **kwargs)
    if not (hasattr(cb.func, '_nr_last_object') and
            hasattr(cb.func._nr_last_object, '_nr_recorded_exception')):
        record_exception(sys.exc_info())

    return wrapped(*args, **kwargs)

def _nr_wrapper_PollIOLoop_remove_timeout(wrapped, instance, args, kwargs):

    # Once a timeout is canceled, it's callback will be set to None, in this
    # case we have already decremented our counter

    def _callback_extractor(timeout, *args, **kwargs):
        if timeout.callback is None:
                return None
        else:
            try:
                return timeout.callback.func
            except:
                _logger.error('Runtime instrumentation error. A callback is '
                        'registered on the ioloop that isn\'t wrapped in '
                        'functools.partial. Perhaps a nonstandard IOLoop is '
                        'being used?')
                return None

    callback = _callback_extractor(*args, **kwargs)

    transaction = getattr(callback, '_nr_transaction', None)

    ret = wrapped(*args, **kwargs)

    if transaction is not None:
        if not hasattr(callback, '_nr_callback_ran'):

            thread_id = current_thread_id()
            if transaction.thread_id != thread_id:
                _logger.debug('ioloop.remove_timeout being called from a '
                        'different thread as the transaction. Callback with ID '
                        '%r, was scheduled in thread %r and removed in thread '
                        '%r. This could potentially cause a race condition that'
                        ' could cause the agent to lose data on this '
                        'transaction.', id(callback), transaction.thread_id,
                        thread_id)

            transaction._ref_count -= 1

            # Finalize the transaction if this is the last callback, this should
            # only be possible if remove_timeout was called from a thread.
            possibly_finalize_transaction(transaction)

    return ret

def _increment_ref_count(callback, wrapped, instance, args, kwargs):
    transaction = retrieve_current_transaction()

    if hasattr(callback, '_nr_transaction'):

        if callback._nr_transaction is not None:
            if current_thread_id() != callback._nr_transaction.thread_id:
                # Callback being added not in the main thread; ignore.

                # Since we are not incrementing the counter for this callback,
                # we need to remove the transaction from the callback, so it
                # doesn't get decremented either.
                callback._nr_transaction = None
                return wrapped(*args, **kwargs)

        if transaction is not callback._nr_transaction:
            _logger.error('Attempt to add callback to ioloop with different '
                    'transaction attached than in the cache. Please report this'
                    ' issue to New Relic support.\n%s',
                    ''.join(traceback.format_stack()[:-1]))

            # Since we are not incrementing the counter for this callback,
            # we need to remove the transaction from the callback, so it doesn't
            # get decremented either.
            callback._nr_transaction = None
            return wrapped(*args, **kwargs)

    if transaction is None:
        return wrapped(*args, **kwargs)

    transaction._ref_count += 1

    return wrapped(*args, **kwargs)

def _nr_wrapper_PollIOLoop_add_callback(wrapped, instance, args, kwargs):

    def _callback_extractor(callback, *args, **kwargs):
        return callback
    callback = _callback_extractor(*args, **kwargs)

    return _increment_ref_count(callback, wrapped, instance, args, kwargs)

def _nr_wrapper_PollIOLoop_call_at(wrapped, instance, args, kwargs):

    def _callback_extractor(deadline, callback, *args, **kwargs):
        return callback
    callback = _callback_extractor(*args, **kwargs)

    return _increment_ref_count(callback, wrapped, instance, args, kwargs)

def instrument_tornado_ioloop(module):
    wrap_function_wrapper(module, 'IOLoop._run_callback',
            _nr_wrapper_IOLoop__run_callback_)
    wrap_function_wrapper(module, 'IOLoop.handle_callback_exception',
            _nr_wrapper_IOLoop_handle_callback_exception_)
    wrap_function_wrapper(module, 'PollIOLoop.add_callback',
            _nr_wrapper_PollIOLoop_add_callback)
    wrap_function_wrapper(module, 'PollIOLoop.call_at',
            _nr_wrapper_PollIOLoop_call_at)
    wrap_function_wrapper(module, 'PollIOLoop.remove_timeout',
            _nr_wrapper_PollIOLoop_remove_timeout)
