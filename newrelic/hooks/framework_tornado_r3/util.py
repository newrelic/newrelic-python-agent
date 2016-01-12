import logging

from newrelic.agent import (application as application_instance,
        current_transaction, ignore_status_code, function_wrapper,
        callable_name, FunctionTrace)

_logger = logging.getLogger(__name__)


# To pass the name of the coroutine back we attach it as an attribute to a
# returned value. If this returned value is None, we instead pass up a
# NoneProxy object with the attribute. When the attribute is consumed we must
# restore the None value.
class NoneProxy(object):
    pass

def record_exception(exc_info):
    # Record the details of any exception ignoring status codes which
    # have been configured to be ignored.

    import tornado.web

    exc = exc_info[0]
    value = exc_info[1]

    # Not an error so we just return.
    if exc is tornado.web.Finish:
        return

    if exc is tornado.web.HTTPError:
        if ignore_status_code(value.status_code):
            return

    transaction = retrieve_current_transaction()
    if transaction:
        transaction.record_exception(*exc_info)
    else:
        # If we are not in a transaction we record the exception to the default
        # application specified in the agent configuration.
        application = application_instance()
        if application and application.enabled:
            application.record_exception(*exc_info)

def retrieve_current_transaction():
    # Retrieves the current transaction regardless of whether it has
    # been stopped or ignored. We sometimes want to purge the current
    # transaction from the transaction cache and remove it with the
    # known current transaction that is being called into asynchronously.

    return current_transaction(active_only=False)

def retrieve_request_transaction(request):
    # Retrieves any transaction already associated with the request.
    return getattr(request, '_nr_transaction', None)

def retrieve_transaction_request(transaction):
    # Retrieves any request already associated with the transaction.
    request_weakref = getattr(transaction, '_nr_current_request', None)
    if request_weakref is not None:
        return request_weakref()
    return None

# We sometimes want to purge the current transaction out of the queue and
# replace it with the known current transaction which has been called into
# asynchronously.
def purge_current_transaction():
    old_transaction = retrieve_current_transaction()
    if old_transaction is not None:
        old_transaction.drop_transaction()
    return old_transaction

def replace_current_transaction(new_transaction):
    old_transaction = purge_current_transaction()
    if new_transaction:
        new_transaction.save_transaction()
    return old_transaction

def finalize_request_monitoring(request, exc=None, value=None, tb=None):
    # Finalize monitoring of the transaction.
    transaction = retrieve_request_transaction(request)
    try:
        finalize_transaction(transaction, exc, value, tb)
    finally:
        # This should be set to None in finalize transaction but in case it
        # isn't we set it to None here.
        request._nr_transaction = None

def finalize_transaction(transaction, exc=None, value=None, tb=None):
    if transaction is None:
        _logger.error('Runtime instrumentation error. Attempting to finalize '
                'an empty transaction. Please report this issue to New Relic '
                'support.\n%s', ''.join(traceback.format_stack()[:-1]))
        return

    old_transaction = replace_current_transaction(transaction)

    try:
        transaction.__exit__(exc, value, tb)

    finally:
        transaction._is_finalized = True
        request = retrieve_transaction_request(transaction)
        if request is not None:
            request._nr_transaction = None
        transaction._nr_current_request = None

        # We place the previous transaction back in the cache unless
        # it is the transaction that just completed.
        if old_transaction != transaction:
            replace_current_transaction(old_transaction)

def create_transaction_aware_fxn(fxn):
    # Returns a version of fxn that will switch context to the appropriate
    # transaction and then restore the previous transaction on exit.
    # If fxn is already transaction aware or if there is no transaction
    # associated with fxn, this will return None.

    # If fxn already has the stored transaction we don't want to rewrap it
    # since this is also cause Tornado's stack_context.wrap to rewrap it.
    # That Tornado method will also return the input fxn immediately if
    # previously wrapped.

    if fxn is None or hasattr(fxn, '_nr_transaction'):
        return None

    # We want to get the transaction associated with this path of execution
    # whether or not we are actively recording information about it.
    transaction = retrieve_current_transaction()

    @function_wrapper
    def transaction_aware(wrapped, instance, args, kwargs):
        old_transaction = replace_current_transaction(transaction)
        name = callable_name(fxn)
        if transaction is None:

            # A transaction will be None for fxns scheduled on the ioloop not
            # associated with a transaction. We want to preserve this make sure
            # then that there is no transaction in the cache when fxn is run.
            ret = fxn(*args, **kwargs)
        else:
            with FunctionTrace(transaction, name=name) as ft:
                ret = fxn(*args, **kwargs)
                # Coroutines are wrapped in lambdas when they are scheduled.
                # See tornado.gen.Runner.run(). In this case, we don't know the
                # name until the function is run. We only know it then because we
                # pass out the name as an attribute on the result.
                # We update the name now.
                if (ft is not None and ret is not None and
                        hasattr(ret, '_nr_coroutine_name')):
                    ft.name = ret._nr_coroutine_name
                    # To be able to attach the name to the return value of a
                    # coroutine we need to have the coroutine return an object.
                    # If it returns None, we have created a proxy object. We now
                    # restore the original None value.
                    if type(ret) == NoneProxy:
                        ret = None

        replace_current_transaction(old_transaction)
        return ret

    return transaction_aware(fxn)
