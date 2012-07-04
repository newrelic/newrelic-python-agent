from __future__ import with_statement

import functools
import inspect

from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import current_transaction
from newrelic.api.object_wrapper import (ObjectWrapper,
        callable_name, wrap_object)
from newrelic.core.function_node import FunctionNode

class FunctionTrace(TimeTrace):

    def __init__(self, transaction, name, group=None):
        super(FunctionTrace, self).__init__(transaction)

        self.name = name
        self.group = group or 'Function'

    def dump(self, file):
        print >> file, self.__class__.__name__, dict(name=self.name,
                group=self.group)

    def create_node(self):
        return FunctionNode(group=self.group, name=self.name,
                children=self.children, start_time=self.start_time,
                end_time=self.end_time, duration=self.duration,
                exclusive=self.exclusive)

def FunctionTraceWrapper(wrapped, name=None, group=None):

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(name):
            if instance and inspect.ismethod(wrapped):
                _name = name(instance, *args, **kwargs)
            else:
                _name = name(*args, **kwargs)

        elif name is None:
            _name = callable_name(wrapped)

        else:
            _name = name

        if callable(group):
            if instance and inspect.ismethod(wrapped):
                _group = group(instance, *args, **kwargs)
            else:
                _group = group(*args, **kwargs)

        else:
            _group = group

        with FunctionTrace(transaction, _name, _group):
            return wrapped(*args, **kwargs)

    def literal_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        _name = name or callable_name(wrapped)

        with FunctionTrace(transaction, _name, group):
            return wrapped(*args, **kwargs)

    if callable(name) or callable(group):
        return ObjectWrapper(wrapped, None, dynamic_wrapper)

    return ObjectWrapper(wrapped, None, literal_wrapper)

def function_trace(name=None, group=None):
    return functools.partial(FunctionTraceWrapper, name=name, group=group)

def wrap_function_trace(module, object_path, name=None, group=None):
    wrap_object(module, object_path, FunctionTraceWrapper, (name, group))
