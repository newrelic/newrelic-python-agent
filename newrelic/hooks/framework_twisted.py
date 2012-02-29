import types
import urllib
import sys
import weakref
import UserList

import newrelic.api.object_wrapper
import newrelic.api.transaction
import newrelic.api.web_transaction
import newrelic.api.function_trace
import newrelic.api.error_trace

class RequestProcessWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __call__(self):
        assert self._nr_instance != None

        transaction = newrelic.api.transaction.transaction()

        # Check to see if we are being called within the
        # context of any sort of transaction. If we are,
        # then we don't bother doing anything and just
        # call the wrapped function. This should not really
        # ever occur with Twisted Web wrapper but check
        # anyway.

        if transaction:
            return self._nr_next_object()

        # Always use the default application specified in
        # the agent configuration.

        application = newrelic.api.application.application()

        # We need to fake up a WSGI like environ dictionary
        # with the key bits of information we need.

        environ = {}

        environ['REQUEST_URI'] = self._nr_instance.path

        # Now start recording the actual web transaction.
 
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)

        if not transaction.enabled:
            return self._nr_next_object()

        transaction.__enter__()

        self._nr_instance._nr_transaction = transaction

        self._nr_instance._nr_is_deferred_callback = False
        self._nr_instance._nr_is_request_finished = False
        self._nr_instance._nr_wait_function_trace = None

        # Need to add reference back to request object in the
        # transaction as only able to stash the transaction in a
        # deferred. Need to use a weakref to avoid an object
        # cycle which may prevent cleanup of transaction.

        transaction._nr_current_request = weakref.ref(self._nr_instance)

        try:
            # Call the original method in a trace object to give
            # better context in transaction traces. Two things
            # can happen within this call. The render function
            # which is in turn called can return result
            # immediately which means finish() gets called on
            # request, or it can return that it is not done yet
            # and register deferred callbacks to complete the
            # request.

            with newrelic.api.function_trace.FunctionTrace(transaction,
                    name='Resource/Render', group='Python/Twisted'):
                result = self._nr_next_object()

            # In the case of a result having being returned then
            # finish() will have been called. We can't just exit
            # the transaction in the finish call however as need
            # to still pop back up through the above function
            # trace. So if flagged that have finished, then we
            # exit the transation here. Otherwise we setup a
            # function trace to track wait time for deferred and
            # manually pop the transaction as being the current
            # one for this thread.

            #if self._nr_instance.finished:
            if self._nr_instance._nr_is_request_finished:
                transaction.__exit__(None, None, None)
                self._nr_instance = None

            else:
                self._nr_instance._nr_wait_function_trace = \
                        newrelic.api.function_trace.FunctionTrace(
                        transaction, name='Deferred/Wait',
                        group='Python/Twisted')
                self._nr_instance._nr_wait_function_trace.__enter__()
                # XXX This wasn't inside of if before.
                transaction._drop_transaction(transaction)
        except:
            # If an error occurs assume that transaction should
            # be exited. Not sure if this is completely correct
            # thing to do in all cases.

            #transaction.notice_error(*sys.exc_info())
            transaction.__exit__(*sys.exc_info())
            self._nr_instance = None
            raise

        return result

class RequestFinishWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __call__(self):
        assert self._nr_instance != None

        if not hasattr(self._nr_instance, '_nr_transaction'):
            return self._nr_next_object()

        transaction = self._nr_instance._nr_transaction

        if not newrelic.api.transaction.transaction():
            transaction._save_transaction(transaction)

        # We might get hear through Twisted itself somehow
        # calling finish() when still waiting for a deferred.
        # Not sure if this can occur, but check anyway and
        # end the function trace node.

        if self._nr_instance._nr_wait_function_trace:
            self._nr_instance._nr_wait_function_trace.__exit__(None, None, None)
            self._nr_instance._nr_wait_function_trace = None

        # We can't actually exit the transaction at this point
        # as may be called in context of an outer function
        # trace node. We thus flag that are finished and pop
        # back out allowing outer scope to actually exit the
        # transaction.

        self._nr_instance._nr_is_request_finished = True

        # Now call the original finish() function. If we are in
        # a deferred log any error against the transaction here
        # so know capture it. We possibly don't need to do it
        # here as outer scope may catch it anyway. Duplicate
        # will be ignored so not too important. Hopefully the
        # finish() call would never fail anyway.

        if self._nr_instance._nr_is_deferred_callback:
            try:
                result = self._nr_next_object()
            except:
                transaction.notice_error(*sys.exc_info())
                raise

        else:
            try:
                #self._nr_instance = None
                result = self._nr_next_object()
                #transaction.__exit__(None, None, None)
            except:
                #transaction.__exit__(*sys.exc_info())
                raise

        return result

class ResourceRenderWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __call__(self, *args):
        assert self._nr_instance != None

	# Temporary work around due to customer calling class
	# method directly with 'self' as first argument.

        request = args[-1]

        transaction = newrelic.api.transaction.transaction()

        if transaction is not None:
            name = "%s.render_%s" % (
                    newrelic.api.object_wrapper.callable_name(
                    self._nr_instance), request.method)
            transaction.name_transaction(name, priority=1)

            with newrelic.api.function_trace.FunctionTrace(transaction, name):
                return self._nr_next_object(*args)

        return self._nr_next_object(*args)

class DeferredUserList(UserList.UserList):

    def pop(self, i=-1):
        import twisted.internet.defer
        item = super(DeferredUserList, self).pop(i)

        item0 = item[0]
        item1 = item[1]

        if item0[0] != twisted.internet.defer._CONTINUE:
            item0 = (newrelic.api.function_trace.FunctionTraceWrapper(
                     item0[0], group='Python/Twisted/Callback'),
                     item0[1], item0[2])

        if item1[0] != twisted.internet.defer._CONTINUE:
            item1 = (newrelic.api.function_trace.FunctionTraceWrapper(
                     item1[0], group='Python/Twisted/Errback'),
                     item1[1], item1[2])

        return (item0, item1)

class DeferredWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __call__(self, *args, **kwargs):
        self._nr_next_object(*args, **kwargs)

        if self._nr_instance:
            transaction = newrelic.api.transaction.transaction()
            if transaction:
                self._nr_instance._nr_transaction = transaction
                self._nr_instance.callbacks = DeferredUserList(
                        self._nr_instance.callbacks)

class DeferredCallbacksWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __call__(self):
        assert self._nr_instance != None

        transaction = newrelic.api.transaction.transaction()

        if transaction:
            return self._nr_next_object()

        if not hasattr(self._nr_instance, '_nr_transaction'):
            return self._nr_next_object()

        transaction = self._nr_instance._nr_transaction

        if not hasattr(transaction, '_nr_current_request'):
            return self._nr_next_object()

        request = transaction._nr_current_request()

        if not request:
            return self._nr_next_object()
        
        try:
            transaction._save_transaction(transaction)
            request._nr_is_deferred_callback = True
            if request._nr_wait_function_trace:
                request._nr_wait_function_trace.__exit__(None, None, None)
                request._nr_wait_function_trace = None
            with newrelic.api.error_trace.ErrorTrace(transaction):
                with newrelic.api.function_trace.FunctionTrace(
                        transaction, name='Deferred/Call',
                        group='Python/Twisted'):
                    return self._nr_next_object()
        finally:
            if request._nr_is_request_finished:
                transaction.__exit__(None, None, None)
            else:
                request._nr_wait_function_trace = \
                        newrelic.api.function_trace.FunctionTrace(
                        transaction, name='Deferred/Wait',
                        group='Python/Twisted')
                request._nr_wait_function_trace.__enter__()
                transaction._drop_transaction(transaction)
            request._nr_is_deferred_callback = False

class InlineGeneratorWrapper(object):

    def __init__(self, wrapped, generator):
        self._nr_wrapped = wrapped
        self._nr_generator = generator

    def __iter__(self):
        name = newrelic.api.object_wrapper.callable_name(self._nr_wrapped)
        iterable = iter(self._nr_generator)
        while 1:
            transaction = newrelic.api.transaction.transaction()
            with newrelic.api.function_trace.FunctionTrace(
                  transaction, name, group='Python/Twisted/Generator'):
                yield next(iterable)
        
class InlineCallbacksWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()

        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        result = self._nr_next_object(*args, **kwargs)

        if not result:
            return result

        return iter(InlineGeneratorWrapper(self._nr_next_object, result))

def instrument_twisted_web_server(module):
    module.Request.process = RequestProcessWrapper(module.Request.process)

def instrument_twisted_web_http(module):
    module.Request.finish = RequestFinishWrapper(module.Request.finish)

def instrument_twisted_web_resource(module):
    module.Resource.render = ResourceRenderWrapper(module.Resource.render)

def instrument_twisted_internet_defer(module):
    module.Deferred.__init__ = DeferredWrapper(module.Deferred.__init__)
    module.Deferred._runCallbacks = DeferredCallbacksWrapper(
            module.Deferred._runCallbacks)

    _inlineCallbacks = module.inlineCallbacks

    def inlineCallbacks(f):
        return _inlineCallbacks(InlineCallbacksWrapper(f))

    #module.inlineCallbacks = inlineCallbacks
