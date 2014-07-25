import sys
import itertools

from newrelic.agent import (wrap_function_wrapper, current_transaction,
    FunctionTrace, callable_name)

from . import (retrieve_request_transaction, initiate_request_monitoring,
    suspend_request_monitoring, resume_request_monitoring,
    finalize_request_monitoring, record_exception)

def call_wrapper(wrapped, instance, args, kwargs):
    def _args(request, *args, **kwargs):
        return request

    request = _args(*args, **kwargs)

    # If no transaction associated with request already, need to
    # create a new one. The exception is when the the ASYNC API is
    # being executed within a WSGI application, in which case a
    # transaction will already be active. For that we execute
    # straight away.

    if instance._wsgi:
        transaction = current_transaction()

        with FunctionTrace(transaction, name='Request/Process',
                group='Python/Tornado'):
            return wrapped(*args, **kwargs)

    transaction = retrieve_request_transaction(request)

    if transaction is None:
        transaction = initiate_request_monitoring(request)

    if not transaction:
        return wrapped(*args, **kwargs)

    try:
        # Call the original method in a trace object to give better
        # context in transaction traces.

        with FunctionTrace(transaction, name='Request/Process',
                group='Python/Tornado'):
            handler = wrapped(*args, **kwargs)

    except:  # Catch all
        finalize_request_monitoring(request, *sys.exc_info())
        raise

    else:
        # In the case of an immediate result or an exception
        # occuring, then finish() will have been called on the
        # request already. We can't just exit the transaction in the
        # finish call however as need to still pop back up through
        # the above function trace. So if it has been flagged that
        # it is finished, which Tornado does by setting the request
        # object in the connection to None, then we exit the
        # transaction here. Otherwise we setup a function trace to
        # track wait time for deferred and manually pop the
        # transaction as being the current one for this thread.

        if handler._finished:
            if not request.connection.stream.writing():
                finalize_request_monitoring(request)

            else:
                suspend_request_monitoring(request, name='Request/Output')

        else:
            suspend_request_monitoring(request, name='Callback/Wait')

        return handler

def execute_wrapper(wrapped, instance, args, kwargs):
    assert instance is not None

    handler = instance
    request = handler.request

    # Check to see if we are being called within the context of any
    # sort of transaction. If we are, then we don't bother doing
    # anything and just call the wrapped function. This should not
    # really ever occur but check anyway.

    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    if request.method not in handler.SUPPORTED_METHODS:
        return wrapped(*args, **kwargs)

    name = callable_name(getattr(handler, request.method.lower()))
    transaction.set_transaction_name(name)

    with FunctionTrace(transaction, name=name):
        return wrapped(*args, **kwargs)

def error_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is not None:
        record_exception(transaction, sys.exc_info())

    return wrapped(*args, **kwargs)

def render_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = callable_name(wrapped)
    with FunctionTrace(transaction, name=name):
        return wrapped(*args, **kwargs)

def finish_wrapper(wrapped, instance, args, kwargs):
    assert instance is not None

    handler = instance
    request = handler.request

    # Call wrapped method straight away if request object it is
    # being called on is not even associated with a transaction.
    # If we were in a running transaction we still want to record
    # the call though. This will occur when calling finish on
    # another request, but the target request wasn't monitored.

    transaction = retrieve_request_transaction(request)

    running_transaction = current_transaction()

    if not transaction:
        if running_transaction:
            name = callable_name(wrapped)

            with FunctionTrace(transaction, name):
                return wrapped(*args, **kwargs)

        else:
            return wrapped(*args, **kwargs)

    # Do we have a running transaction. When we do we need to
    # consider two possiblities. The first is where the current
    # running transaction doesn't match that bound to the request.
    # For this case it would be where from within one transaction
    # there is an attempt to call finish() on a distinct web request
    # which was being monitored. The second is where finish() is
    # being called for the current request.

    if running_transaction:
        if transaction != running_transaction:
            # For this case we need to suspend the current running
            # transaction and call ourselves again. When it returns
            # we need to restore things back the way they were.
            # We still trace the call in the running transaction
            # though so the fact that it called finish on another
            # request is apparent.

            name = callable_name(wrapped)

            with FunctionTrace(running_transaction, name):
                try:
                    running_transaction.drop_transaction()

                    return finish_wrapper(wrapped, instance, args, kwargs)

                finally:
                    running_transaction.save_transaction()

        else:
            # For this case we just trace the call.

            name = callable_name(wrapped)

            with FunctionTrace(transaction, name):
                return wrapped(*args, **kwargs)

    # Attempt to resume the transaction, calling the wrapped method
    # straight away if there isn't one. Otherwise trace the call.

    transaction = resume_request_monitoring(request)

    if transaction is None:
        return wrapped(*args, **kwargs)

    try:
        name = callable_name(wrapped)

        with FunctionTrace(transaction, name):
            result = wrapped(*args, **kwargs)

    except:  # Catch all
        finalize_request_monitoring(request, *sys.exc_info())
        raise

    else:
        if not request.connection.stream.writing():
            finalize_request_monitoring(request)

        else:
            suspend_request_monitoring(request, name='Request/Output')

        return result

def generate_headers_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    transaction._thread_utilization_start = None

    status = '%d ???' % instance.get_status()

    # The HTTPHeaders class with get_all() only started to
    # be used in Tornado 3.0. For older versions have to fall
    # back to combining the dictionary and list of headers.

    try:
        response_headers = instance._headers.get_all()

    except AttributeError:
        try:
            response_headers = itertools.chain(
                    instance._headers.items(),
                    instance._list_headers)

        except AttributeError:
            response_headers = itertools.chain(
                    instance._headers.items(),
                    instance._headers)

    additional_headers = transaction.process_response(
            status, response_headers, *args)

    for name, value in additional_headers:
        instance.add_header(name, value)

    return wrapped(*args, **kwargs)

def on_connection_close_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction:
        return wrapped(*args, **kwargs)

    handler = instance
    request = handler.request

    transaction = resume_request_monitoring(request)

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = callable_name(wrapped)

    try:
        with FunctionTrace(transaction, name):
            result = wrapped(*args, **kwargs)

    except:  # Catch all
        finalize_request_monitoring(request, *sys.exc_info())
        raise

    else:
        finalize_request_monitoring(request)

        return result

def init_wrapper(wrapped, instance, args, kwargs):
    # In this case we are actually wrapping the instance method on an
    # actual instance of a handler class rather than the class itself.
    # This is so we can wrap any derived version of this method when
    # it has been overridden in a handler class.

    wrap_function_wrapper(instance, 'on_connection_close',
            on_connection_close_wrapper)

    return wrapped(*args, **kwargs)

def instrument_tornado_web(module):
    wrap_function_wrapper(module, 'Application.__call__', call_wrapper)
    wrap_function_wrapper(module, 'RequestHandler._execute', execute_wrapper)
    wrap_function_wrapper(module, 'RequestHandler._handle_request_exception',
            error_wrapper)

    # XXX This mucks up Tornado's calculation of where template file
    # is as it does walking of the stack frames to work it out and the
    # wrapper makes it stop before getting to the users code.

    #wrap_function_wrapper(module, 'RequestHandler.render', render_wrapper)
    #wrap_function_wrapper(module, 'RequestHandler.render_string',
    #        render_wrapper)

    wrap_function_wrapper(module, 'RequestHandler.finish', finish_wrapper)
    wrap_function_wrapper(module, 'RequestHandler._generate_headers',
            generate_headers_wrapper)

    wrap_function_wrapper(module, 'RequestHandler.__init__', init_wrapper)

