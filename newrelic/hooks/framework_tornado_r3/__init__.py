import logging

from newrelic.agent import current_transaction

_logger = logging.getLogger(__name__)

def record_exception(transaction, exc_info):
    # Record the details of any exception ignoring status codes which
    # have been configured to be ignored.

    import tornado.web

    exc = exc_info[0]
    value = exc_info[1]

    if exc is tornado.web.HTTPError:
        if ignore_status_code(value.status_code):
            return

    transaction.record_exception(*exc_info)

def retrieve_current_transaction():
    # Retrieves the current transaction regardless of whether it has
    # been stopped or ignored. We sometimes want to purge the current
    # transaction from the transaction cache and remove it with the
    # known current transaction that is being called into asynchronously.

    return current_transaction(active_only=False)

def retrieve_request_transaction(request):
    # Retrieves any transaction already associated with the request.
    return getattr(request, '_nr_transaction', None)

# We sometimes want to purge the current transaction out of the queue and
# replace it with the known current transaction which has been called into
# asynchronously.
def purge_current_transaction():
    old_transaction = retrieve_current_transaction()
    if old_transaction is not None:
        old_transaction.drop_transaction()

# TODO(bdirks): I feel like there may be a problem with a threadid pointing to
# None. We should never store None in the transaction cache. I need to
# investigate whether this will happen now.
def replace_current_transaction(new_transaction):
    purge_current_transaction()
    new_transaction.save_transaction()

def finalize_request_monitoring(request, exc=None, value=None, tb=None):
    purge_current_transaction()

    # Finalize monitoring of the transaction.
    transaction = retrieve_request_transaction(request)
    transaction.save_transaction()

    if transaction is None:
        _logger.error('Runtime instrumentation error. Finalizing the '
                'Tornado transaction but there was no transaction cached '
                'against the request object. Report this issue to New Relic '
                'support.\n%s', ''.join(traceback.format_stack()[:-1]))
        return

    # If all nodes haven't been popped from the transaction stack then
    # error messages will be logged by the transaction. We therefore do
    # not need to check here.
    #
    # We must ensure we cleanup here even if __exit__() fails with an
    # exception for some reason.

    try:
        transaction.__exit__(exc, value, tb)

    finally:
        transaction._nr_current_request = None
        request._nr_transaction = None
