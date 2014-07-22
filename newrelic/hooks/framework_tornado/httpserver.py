import logging
import sys
import weakref
import types
import itertools
import traceback

from newrelic.agent import (wrap_function_wrapper, current_transaction,
        FunctionTrace, wrap_function_trace, callable_name)

from . import (retrieve_request_transaction, initiate_request_monitoring,
    suspend_request_monitoring, resume_request_monitoring,
    finalize_request_monitoring)

_logger = logging.getLogger(__name__)

def on_headers_wrapper(wrapped, instance, args, kwargs):
    # This is the first point at which we should ever be called for a
    # request. It is called when the request headers have been read in.
    # The next phase would be to read in any request content but we
    # can't tell whether that will happen or not at this point. We do
    # need to setup a callback when connection is closed due to client
    # disconnecting.

    assert instance is not None

    connection = instance

    # Check to see if we are being called within the context of any sort
    # of transaction. If we are, then we don't bother doing anything and
    # just call the wrapped function. This should not really ever occur
    # but check anyway.

    transaction = current_transaction()

    if transaction:
        return wrapped(*args, **kwargs)

    # Execute the wrapped function as we are only going to do something
    # after it has been called.

    result = wrapped(*args, **kwargs)

    # Check to see if the connection has already been closed or the
    # request finished. The connection can be closed where request
    # content length was too big.

    if connection.stream.closed():
        return result

    if connection._request_finished:
        return result

    # Check to see if we have already associated a transaction with the
    # request, because if we have for some reason, even if not finished,
    # then do not need to do anything.

    request = connection._request

    if request is None:
        return result

    transaction = retrieve_request_transaction(request)

    if transaction is not None:
        return result

    # Create the transaction but if it is None then it means recording
    # of transactions is not enabled then do not need to to anything.

    transaction = initiate_request_monitoring(request)

    if transaction is None:
        return result

    # Add a callback variable to the connection object so we can be
    # notified when the connection is closed before all content has been
    # read. This will be invoked from _maybe_run_close_callback() of
    # the stream object.

    def _close():
        transaction = resume_request_monitoring(request)

        if transaction is None:
            return

        # Force a function trace to record the fact that the socket
        # connection was closed due to client disconnection.

        with FunctionTrace(transaction, name='Request/Close',
                group='Python/Tornado'):
            pass

        finalize_request_monitoring(request)

    connection.stream._nr_close_callback = _close

    # Name transaction initially after the wrapped function so that if
    # connection dropped before request content read, then don't get
    # metric grouping issues with it being named after the URL.

    name = callable_name(wrapped)

    transaction.set_transaction_name(name)

    # Now suspend monitoring of current transaction until next callback.

    suspend_request_monitoring(request, name='Request/Input')

    return result

def on_request_body_wrapper(wrapped, instance, args, kwargs):
    # Called when there was a request body and it has now all been
    # read in and buffered ready to call the request handler.

    assert instance is not None

    connection = instance
    request = connection._request

    # Wipe out our temporary callback for being notified that the
    # connection is being closed before content is read.

    connection.stream._nr_close_callback = None

    # Restore any transaction which may have been suspended.

    transaction = resume_request_monitoring(request)

    # Now call the orginal wrapped function. It will in turn call the
    # application which will ensure any transaction which was resumed
    # here is popped off. We cannot use a function trace at this point
    # even if in a transaction as the called function can suspend
    # the transaction or even finalize it.

    return wrapped(*args, **kwargs)

def finish_request_wrapper(wrapped, instance, args, kwargs):
    # Normally called when the request is all complete meaning that
    # we have to finalize our own transaction. We may actually enter
    # here with the transaction already being the current one.

    assert instance is not None

    connection = instance
    request = connection._request

    # Deal first with possibility that the transaction is already
    # the current active transaction.

    transaction = retrieve_request_transaction(request)

    if transaction == current_transaction():
        # XXX Old code has stuff to undo a function trace????

        # XXX FINISH

        request._nr_request_finished = True

        return wrapped(*args, **kwargs)

    # Not the current active transaction and thereby assume that there
    # is no current active transaction and we need to try and resume
    # the transaction associated with the request.

    assert transaction is None

    transaction = resume_request_monitoring(request)

    if transaction is None:
        return wrapped(*args, **kwargs)

    # XXX Old code has stuff to undo a function trace????

    # XXX FINISH

    request._nr_request_finished = True

    try:
        result = wrapped(*args, **kwargs)

    except:  # Catch all
        finalize_request_monitoring(request, *sys.exc_info())
        raise

    finalize_request_monitoring(request)

    return result

def finish_wrapper(wrapped, instance, args, kwargs):
    # Called when a request handler which was operating in async mode
    # indicated that the request had been finished. We have to deal
    # with some odd cases here as one request could call close for a
    # different request.

    assert instance is not None

    request = instance

    # Call wrapped method straight away if request object it is being
    # called on is not even associated with a transaction.

    transaction = retrieve_request_transaction(request)

    if not transaction:
        return wrapped(*args, **kwargs)

    # Do we have a running transaction. When we do we need to consider
    # two possiblities. The first is where the current running
    # transaction doesn't match that bound to the request. For this case
    # it would be where from within one transaction there is an attempt
    # to call finish() on a distinct web request which was being
    # monitored. The second is where finish() is being called for the
    # current request.

    running_transaction = current_transaction()

    if running_transaction:
        if transaction != running_transaction:
            # For this case we need to suspend the current
            # running transaction and call ourselves again. When
            # it returns we need to restore things back the way
            # they were.

            try:
                running_transaction.drop_transaction()

                return finish_wrapper(wrapped, instance, args, kwargs)

            finally:
                running_transaction.save_transaction()

        else:
            # For this case we just trace the call.

            name = callable_name(wrapped)

            with FunctionTrace(transaction, name=name):
                return wrapped(*args, **kwargs)

    # Now handle the special case where finish() was called while in the
    # wait state. We need to restore the transaction for the request and
    # then call finish(). When it returns we need to either end the
    # transaction or go into a new wait state where we wait on output to
    # be sent.

    transaction = resume_request_monitoring(request)

    if transaction is None:
        return wrapped(*args, **kwargs)

    try:
        name = callable_name(wrapped)

        with FunctionTrace(transaction, name=name):
            result = wrapped(*args, **kwargs)

    except:  # Catch all
        finalize_request_monitoring(request, *sys.exc_info())
        raise

    if not request.connection.stream.writing():
        finalize_request_monitoring(request)

    else:
        suspend_request_monitoring(request, name='Request/Output')

    return result

def instrument_tornado_httpserver(module):
    wrap_function_wrapper(module, 'HTTPConnection._on_headers',
            on_headers_wrapper)
    wrap_function_wrapper(module, 'HTTPConnection._on_request_body',
            on_request_body_wrapper)
    wrap_function_wrapper(module, 'HTTPConnection._finish_request',
            finish_request_wrapper)
    wrap_function_wrapper(module, 'HTTPConnection.finish',
            finish_wrapper)

    if hasattr(module.HTTPRequest, '_parse_mime_body'):
        wrap_function_trace(module.HTTPRequest, '_parse_mime_body')
