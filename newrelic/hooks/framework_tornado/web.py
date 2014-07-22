import logging
import sys
import weakref
import itertools

from newrelic.agent import (wrap_function_wrapper, current_transaction,
        FunctionTrace, wrap_function_trace, callable_name,
        ObjectWrapper, application as application_instance)

from . import (retrieve_request_transaction, initiate_request_monitoring,
    suspend_request_monitoring, resume_request_monitoring,
    finalize_request_monitoring, record_exception)

_logger = logging.getLogger(__name__)

def call_wrapper(wrapped, instance, args, kwargs):
    # We have to deal with a special case here because when using
    # tornado.wsgi.WSGIApplication() to host the async API within
    # a WSGI application, Tornado will call the wrapped method via
    # the class method rather than via an instance. This means the
    # instance will be None and the self argument will actually
    # be the first argument. The args are still left intact for
    # when we call the wrapped function.

    def _request_unbound(instance, request, *args, **kwargs):
        return instance, request

    def _request_bound(request, *args, **kwargs):
        return request

    if instance is None:
        instance, request = _request_unbound(*args, **kwargs)
    else:
        request = _request_bound(*args, **kwargs)

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

    elif not hasattr(request, '_nr_transaction'):
        transaction = initiate_request_monitoring(request)

        if transaction is None:
            return wrapped(*args, **kwargs)

    else:
        # If there was a transaction associated with the request,
        # only continue if a transaction is active though.

        transaction = current_transaction()

        if not transaction:
            return wrapped(*args, **kwargs)

    try:
        # Call the original method in a trace object to give better
        # context in transaction traces.

        with FunctionTrace(transaction, name='Request/Process',
                group='Python/Tornado'):
            handler = wrapped(*args, **kwargs)

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

    except:  # Catch all
        # If an error occurs assume that transaction should be
        # exited. Technically don't believe this should ever occur
        # unless our code here has an error.

        _logger.exception('Unexpected exception raised by Tornado '
                'Application.__call__().')

        finalize_request_monitoring(request, *sys.exc_info())

        raise

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

    # Call finish() method straight away if request object it is
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

    # No current running transaction. If we aren't in a wait state
    # we call finish() straight away.

    if not request._nr_wait_function_trace:
        return wrapped(*args, **kwargs)

    # Now handle the special case where finish() was called while in
    # the wait state. We need to restore the transaction for the
    # request and then call finish(). When it returns we need to
    # either end the transaction or go into a new wait state where
    # we wait on output to be sent.

    transaction.save_transaction()

    try:
        complete = True

        request._nr_wait_function_trace.__exit__(None, None, None)

        name = callable_name(wrapped)

        with FunctionTrace(transaction, name):
            result = wrapped(*args, **kwargs)

        if not request.connection.stream.writing():
            transaction.__exit__(None, None, None)

        else:
            suspend_request_monitoring(request, name='Request/Output')

            complete = False

        return result

    except:  # Catch all
        transaction.__exit__(*sys.exc_info())
        raise

    finally:
        if complete:
            request._nr_wait_function_trace = None
            request._nr_transaction = None

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

    transaction = getattr(request, '_nr_transaction', None)

    if not transaction:
        return wrapped(*args, **kwargs)

    transaction.save_transaction()

    if request._nr_wait_function_trace:
        request._nr_wait_function_trace.__exit__(None, None, None)

    name = callable_name(wrapped)

    try:
        with FunctionTrace(transaction, name):
            return wrapped(*args, **kwargs)

    except Exception:
        transaction.record_exception(*sys.exc_info())

    finally:
        transaction.__exit__(None, None, None)

def init_wrapper(wrapped, instance, args, kwargs):
    if instance:
        # Bound method when RequestHandler instantiated
        # directly.

        handler = instance

    elif args:
        # When called from derived class constructor it is
        # not done so as a bound method. Instead the self
        # object will be passed as the first argument.

        handler = args[0]

    else:
        # Incorrect number of arguments. Pass it through so
        # it fails on call.

        return wrapped(*args, **kwargs)

    handler.on_connection_close = ObjectWrapper(
            handler.on_connection_close, None,
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

