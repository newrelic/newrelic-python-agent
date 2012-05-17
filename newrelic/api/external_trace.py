from __future__ import with_statement

import sys
import types
import inspect
import time

import newrelic.core.external_node

import newrelic.api.transaction
import newrelic.api.time_trace
import newrelic.api.object_wrapper

class ExternalTrace(newrelic.api.time_trace.TimeTrace):

    node = newrelic.core.external_node.ExternalNode

    def __init__(self, transaction, library, url, method=None):
        super(ExternalTrace, self).__init__(transaction)

        self.library = library
        self.url = url
        self.method = method

    def dump(self, file):
        print >> file, self.__class__.__name__, dict(library=self.library,
                url=self.url, method=self.method)

    def create_node(self):
        return self.node(library=self.library, url=self.url,
                method=self.method, children=self.children,
                start_time=self.start_time, end_time=self.end_time,
                duration=self.duration, exclusive=self.exclusive)

    def terminal_node(self):
        return True

class ExternalTraceWrapper(object):

    def __init__(self, wrapped, library, url, method=None):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_library = library
        self._nr_url = url
        self._nr_method = method

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_library,
                              self._nr_url, self._nr_method)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if not isinstance(self._nr_url, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                url = self._nr_url(self._nr_instance, *args, **kwargs)
            else:
                url = self._nr_url(*args, **kwargs)
        else:
            url = self._nr_url

        if (self._nr_method is not None and
                not isinstance(self._nr_method, basestring)):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                method = self._nr_method(self._nr_instance, *args, **kwargs)
            else:
                method = self._nr_method(*args, **kwargs)
        else:
            method = self._nr_method

        with ExternalTrace(transaction, self._nr_library, url, method):
            return self._nr_next_object(*args, **kwargs)

def external_trace(library, url, method=None):
    def decorator(wrapped):
        return ExternalTraceWrapper(wrapped, library, url, method)
    return decorator

def wrap_external_trace(module, object_path, library, url, method=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            ExternalTraceWrapper, (library, url, method))
