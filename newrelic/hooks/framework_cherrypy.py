from __future__ import with_statement

import sys
import types

import newrelic.api.transaction
import newrelic.api.web_transaction
import newrelic.api.function_trace
import newrelic.api.object_wrapper
import newrelic.api.error_trace

class HandlerWrapper(object):

    def __init__(self, wrapped):
        self.__name = newrelic.api.object_wrapper.callable_name(wrapped)
        self.__wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__(descriptor)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.current_transaction()
        if transaction:
            transaction.name_transaction(name=self.__name, priority=2)
            with newrelic.api.error_trace.ErrorTrace(transaction):
                with newrelic.api.function_trace.FunctionTrace(
                        transaction, name=self.__name):
                    try:
                        return self.__wrapped(*args, **kwargs)
                    except:
                        transaction.record_exception(*sys.exc_info())
                        raise
        else:
            return self.__wrapped(*args, **kwargs)

class ResourceWrapper(object):

    def __init__(self, wrapped):
        self.__wrapped = wrapped

    def __dir__(self):
        return dir(self.__wrapped)

    def __getattr__(self, name):
        attr = getattr(self.__wrapped, name)
        if name.isupper():
            return HandlerWrapper(attr)
        return attr

class ResolverWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None
        self.__instance = instance
        self.__wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.current_transaction()
        if transaction:
            try:
                obj, vpath = self.__wrapped(*args, **kwargs)
                if obj:
                    klass = self.__instance.__class__
                    if klass.__name__ == 'MethodDispatcher':
                        transaction.name_transaction('405', group='Uri')
                        obj = ResourceWrapper(obj)
                    else:
                        obj = HandlerWrapper(obj)
                else:
                    transaction.name_transaction('404', group='Uri')
                return obj, vpath
            except:
                transaction.record_exception(*sys.exc_info())
                raise
        else:
            return self.__wrapped(*args, **kwargs)

class RoutesResolverWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None
        self.__instance = instance
        self.__wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.current_transaction()
        if transaction:
            try:
                handler = self.__wrapped(*args, **kwargs)
                if handler:
                    handler = HandlerWrapper(handler)
                else:
                    transaction.name_transaction('404', group='Uri')
                return handler
            except:
                transaction.record_exception(*sys.exc_info())
                raise
        else:
            return self.__wrapped(*args, **kwargs)

def instrument_cherrypy_cpdispatch(module):

    newrelic.api.object_wrapper.wrap_object(module,
            'Dispatcher.find_handler', ResolverWrapper)
    newrelic.api.object_wrapper.wrap_object(module,
            'RoutesDispatcher.find_handler', RoutesResolverWrapper)

def instrument_cherrypy_cpwsgi(module):

    newrelic.api.web_transaction.wrap_wsgi_application(
            module, 'CPWSGIApp.__call__')

def instrument_cherrypy_cptree(module):

    newrelic.api.web_transaction.wrap_wsgi_application(
            module, 'Application.__call__')
