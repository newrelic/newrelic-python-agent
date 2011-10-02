from __future__ import with_statement

import types

import newrelic.api.transaction
import newrelic.api.function_trace
import newrelic.api.object_wrapper

class MethodWrapper(object):

    def __init__(self, wrapped, priority=None):
        self.__name = newrelic.api.object_wrapper.callable_name(wrapped)
        self.__wrapped = wrapped
        self.__priority = priority

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__(descriptor)

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if transaction:
            transaction.name_transaction(self.__name,
                    priority=self.__priority)
            with newrelic.api.function_trace.FunctionTrace(
                    transaction, name=self.__name):
                return self.__wrapped(*args, **kwargs)
        else:
            return self.__wrapped(*args, **kwargs)

class ResourceInitWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None
        self.__instance = instance
        self.__wrapped = wrapped

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self.__wrapped.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __call__(self, *args, **kwargs):
        self.__wrapped(*args, **kwargs)
        handler = self.__instance.handler
        for name in self.__instance.callmap.itervalues():
            if hasattr(handler, name):
                setattr(handler, name, MethodWrapper(
                        getattr(handler, name)))

def instrument_piston_resource(module):

    newrelic.api.object_wrapper.wrap_object(module,
            'Resource.__init__', ResourceInitWrapper)
