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

    def __init__(self, wrapped, application=None):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        # FIXME Probably don't need to be able to accept
        # an application here.

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_application = application

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_application)

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

        # Otherwise treat it as top level transaction.
        # Don't allow way of overriding application like
        # with WSGI, so just lookup up application object.

        application = self._nr_application

        # FIXME Should this allow for multiple apps if a string.

        if type(application) != newrelic.api.application.Application:
            application = newrelic.api.application.application(application)

        # We need to fake up a WSGI like environ dictionary
        # with the key bits of information we need.

        environ = {}

        # FIXME Does this syntax work with Python 2.5.

        environ['REQUEST_URI'] = self._nr_instance.path

        # Now start recording the actual web transaction.
 
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        transaction.__enter__()

        self._nr_instance._nr_transaction = transaction

        self._nr_instance._nr_deferred = False
        self._nr_instance._nr_finished = False
        self._nr_instance._nr_function = None

	# Need to add reference back to request object in the
	# transaction as only able to stash the transaction in a
	# deferred.

        transaction._nr_request = weakref.ref(self._nr_instance)

        try:
            with newrelic.api.function_trace.FunctionTrace(transaction,
                    name='Resource/Render', group='Python/Twisted'):
                result = self._nr_next_object()

            if not self._nr_instance.finished:
                self._nr_instance._nr_function = \
                        newrelic.api.function_trace.FunctionTrace(
                        transaction, name='Deferred/Wait',
                        group='Python/Twisted')
                self._nr_instance._nr_function.__enter__()
            transaction._drop_transaction(transaction)
        except:
            transaction.notice_error(*sys.exc_info())
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

        if self._nr_instance._nr_function:
            self._nr_instance._nr_function.__exit__(None, None, None)
            self._nr_instance._nr_function = None

        if self._nr_instance._nr_deferred:
            self._nr_instance._nr_finished = True
            try:
                result = self._nr_next_object()
            except:
                transaction.notice_error(*sys.exc_info())
                raise

        else:
            try:
                self._nr_instance = None
                result = self._nr_next_object()
                transaction.__exit__(None, None, None)
            except:
                transaction.__exit__(*sys.exc_info())
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

    def __call__(self, request):
        assert self._nr_instance != None

        transaction = newrelic.api.transaction.transaction()

        if transaction is not None:
            name = "%s.render_%s" % (
                    newrelic.api.object_wrapper.callable_name(
                    self._nr_instance), request.method)
            transaction.name_transaction(name, priority=1)

            with newrelic.api.function_trace.FunctionTrace(transaction, name):
                return self._nr_next_object(request)

        return self._nr_next_object(request)

class DeferredUserList(UserList.UserList):

    def pop(self, i=-1):
        import twisted.internet.defer
        item = super(DeferredUserList, self).pop(i)

        item0 = item[0]
        item1 = item[1]

        if item0[0] != twisted.internet.defer._CONTINUE:
            item0 = (newrelic.api.function_trace.FunctionTraceWrapper(
                     item0[0]), item0[1], item0[2])

        if item1[0] != twisted.internet.defer._CONTINUE:
            item1 = (newrelic.api.function_trace.FunctionTraceWrapper(
                     item1[0]), item1[1], item1[2])

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

        if not hasattr(transaction, '_nr_request'):
            return self._nr_next_object()

        request = transaction._nr_request()

        if not request:
            return self._nr_next_object()
        
        try:
            transaction._save_transaction(transaction)
            request._nr_deferred = True
            if request._nr_function:
                request._nr_function.__exit__(None, None, None)
                request._nr_function = None
            with newrelic.api.error_trace.ErrorTrace(transaction):
                with newrelic.api.function_trace.FunctionTrace(
                        transaction, name='Deferred/Call',
                        group='Python/Twisted'):
                    return self._nr_next_object()
        finally:
            if request._nr_finished:
                transaction.__exit__(None, None, None)
            else:
                request._nr_function = \
                        newrelic.api.function_trace.FunctionTrace(
                        transaction, name='Deferred/Wait',
                        group='Python/Twisted')
                request._nr_function.__enter__()
                transaction._drop_transaction(transaction)
            request._nr_deferred = False

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
