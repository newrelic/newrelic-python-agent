from __future__ import with_statement

import logging
import sys
import weakref

from newrelic.api.application import application_instance
from newrelic.api.transaction import current_transaction
from newrelic.api.object_wrapper import ObjectWrapper, callable_name
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.function_trace import FunctionTrace

_logger = logging.getLogger(__name__)

def instrument_tornado_web(module):

    # We want to wrap the __call__ method of an Application class as
    # that is what initially gets called by a HTTPServer for a new
    # request.
    #
    # XXX This may only get called after request body may have been
    # read though.

    def start_wrapper(wrapped, instance, args, kwargs):
        assert instance is not None

        request = args[0]

        # Check to see if we are being called within the context of any
        # sort of transaction. If we are, then we don't bother doing
        # anything and just call the wrapped function. This should not
        # really ever occur but check anyway.

        transaction = current_transaction()

        if transaction:
            return wrapped(*args, **kwargs)

        # Always use the default application specified in the agent
        # configuration.

        application = application_instance()

        # We need to fake up a WSGI like environ dictionary with the key
        # bits of information we need.

        environ = {}

        environ['REQUEST_URI'] = request.uri

        # Now start recording the actual web transaction. Bail out though
        # if turns out that recording transactions is not enabled.

        transaction = WebTransaction(application, environ)

        if not transaction.enabled:
            return wrapped(*args, **kwargs)

        transaction.__enter__()

        request._nr_transaction = transaction

        request._nr_is_deferred_callback = False
        request._nr_wait_function_trace = None

        # We need to add a reference to the request object in to the
        # transaction object as only able to stash the transaction in a
        # deferred. Need to use a weakref to avoid an object cycle which
        # may prevent cleanup of transaction.

        transaction._nr_current_request = weakref.ref(request)

        try:
            # Call the original method in a trace object to give better
            # context in transaction traces.

            with FunctionTrace(transaction, name='Request/Process',
                    group='Python/Tornado'):
                result = wrapped(*args, **kwargs)

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

            if request.connection._request is None:
                transaction.__exit__(None, None, None)
                request._nr_transaction = None

            else:
                request._nr_wait_function_trace = FunctionTrace(
                        transaction, name='Callback/Wait',
                        group='Python/Tornado')

                request._nr_wait_function_trace.__enter__()
                transaction._drop_transaction(transaction)

        except:
            # If an error occurs assume that transaction should be
            # exited. Technically don't believe this should ever occur
            # unless our code here has an error.

            _logger.exception('Unexpected exception raised by Tornado '
                    'Application.__call__().')

            transaction.__exit__(*sys.exc_info())
            request._nr_transaction = None

            raise

        return result

    module.Application.__call__ = ObjectWrapper(
            module.Application.__call__, None, start_wrapper)

    # Also need to wrap the method which executes the request handler.

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
        transaction.name_transaction(name)

        with FunctionTrace(transaction, name=name):
            return wrapped(*args, **kwargs)

    module.RequestHandler._execute = ObjectWrapper(
            module.RequestHandler._execute, None, execute_wrapper)

def instrument_tornado_httpserver(module):

    def finish_wrapper(wrapped, instance, args, kwargs):
        assert instance is not None

        request = instance

        # Call finish() method straight away if request is not even
        # associated with a transaction.

        if not hasattr(request, '_nr_transaction'):
            return wrapped(*args, **kwargs)

        # Technically we should only be able to be called here without
        # an active transaction if we are in the wait state. If we are
        # called in context of original request handler or a deferred
        # the transaction should already be registered.

        transaction = request._nr_transaction

        if request._nr_wait_function_trace:
            if current_transaction():
                _logger.debug('The Tornado request finish() method is '
                        'being called while in wait state but there is '
                        'already a current transaction.')
            else:
                transaction._save_transaction(transaction)

        elif not current_transaction():
            _logger.debug('The Tornado request finish() method is '
                    'being called from request handler or a deferred '
                    'but there is not a current transaction.')

        # Except for case of being called when in wait state, we can't
        # actually exit the transaction at this point as may be called
        # in context of an outer function trace node.  We pop back out
        # allowing outer scope to actually exit the transaction and it
        # will pick up that request finished by seeing that the stream
        # is closed.

        if request._nr_is_deferred_callback:

            # If we are in a deferred callback log any error against the
            # transaction here so we know we will capture it. We
            # possibly don't need to do it here as outer scope may catch
            # it anyway. Duplicate will be ignored so not too important.
            # Most likely the finish() call would never fail anyway.

            try:
                with FunctionTrace(transaction, name='Request/Finish',
                        group='Python/Tornado'):
                    result = wrapped(*args, **kwargs)

            except:
                transaction.record_exception(*sys.exc_info())
                raise

        elif request._nr_wait_function_trace:

            # Now handle the special case where finish() was called
            # while in the wait state. We might get here through Tornado
            # itself somehow calling finish() when still waiting for a
            # deferred. If this were to occur though then the
            # transaction will not be popped if we simply marked request
            # as finished as no outer scope to see that and clean up. We
            # will thus need to end the function trace and exit the
            # transaction. We end function trace here and then the
            # transaction down below.

            try:
                request._nr_wait_function_trace.__exit__(None, None, None)

                with FunctionTrace(transaction, name='Request/Finish',
                        group='Python/Tornado'):
                    result = wrapped(*args, **kwargs)

                transaction.__exit__(None, None, None)

            except:
                transaction.__exit__(*sys.exc_info())
                raise

            finally:
                request._nr_wait_function_trace = None
                request._nr_transaction = None

        else:
            # This should be the case where finish() is being called in
            # the original request handler.

            try:
                with FunctionTrace(transaction, name='Request/Finish',
                        group='Python/Tornado'):
                    result = wrapped(*args, **kwargs)

            except:
                raise

        return result

    module.HTTPRequest.finish = ObjectWrapper(
            module.HTTPRequest.finish, None, finish_wrapper)
