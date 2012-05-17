from __future__ import with_statement

import sys
import types
import inspect
import time

import newrelic.core.function_node

import newrelic.api.transaction
import newrelic.api.time_trace
import newrelic.api.object_wrapper

class FunctionTrace(newrelic.api.time_trace.TimeTrace):

    node = newrelic.core.function_node.FunctionNode

    def __init__(self, transaction, name, group=None):
        super(FunctionTrace, self).__init__(transaction)

        self.name = name
        self.group = group or 'Function'

    def dump(self, file):
        print >> file, self.__class__.__name__, dict(name=self.name,
                group=self.group)

    def create_node(self):
        return self.node(group=self.group, name=self.name,
                children=self.children, start_time=self.start_time,
                end_time=self.end_time, duration=self.duration,
                exclusive=self.exclusive)

class FunctionTraceWrapper(object):

    def __init__(self, wrapped, name=None, group=None):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_name = name
        self._nr_group = group

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_name,
                              self._nr_group)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if self._nr_name is None:
            name = newrelic.api.object_wrapper.callable_name(
                    self._nr_next_object)
        elif not isinstance(self._nr_name, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                name = self._nr_name(self._nr_instance, *args, **kwargs)
            else:
                name = self._nr_name(*args, **kwargs)
        else:
            name = self._nr_name

        if self._nr_group is not None and not isinstance(
                self._nr_group, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                group = self._nr_group(self._nr_instance, *args, **kwargs)
            else:
                group = self._nr_group(*args, **kwargs)
        else:
            group = self._nr_group

        with FunctionTrace(transaction, name, group):
            return self._nr_next_object(*args, **kwargs)

def function_trace(name=None, group=None):
    def decorator(wrapped):
        return FunctionTraceWrapper(wrapped, name, group)
    return decorator

def wrap_function_trace(module, object_path, name=None, group=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            FunctionTraceWrapper, (name, group))
