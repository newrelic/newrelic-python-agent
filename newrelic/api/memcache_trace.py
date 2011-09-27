import sys
import types
import inspect
import time

import newrelic.core.memcache_node

import newrelic.api.transaction
import newrelic.api.object_wrapper

class MemcacheTrace(object):

    def __init__(self, transaction, command):
        self._transaction = transaction

        self._command = command

        self._enabled = False

        self._children = []

        self._start_time = 0.0
        self._end_time = 0.0

    def __enter__(self):
        if not self._transaction:
            return self

        self._enabled = True

        self._start_time = time.time()

        self._transaction._node_stack.append(self)

        return self

    def __exit__(self, exc, value, tb):
        if not self._enabled:
            return

        self._end_time = time.time()

        duration = self._end_time - self._start_time

        exclusive = duration
        for child in self._children:
            exclusive -= child.duration
        exclusive = max(0, exclusive)

        root = self._transaction._node_stack.pop()
        assert(root == self)

        parent = self._transaction._node_stack[-1]

        node = newrelic.core.memcache_node.MemcacheNode(
                command=self._command,
                children=self._children,
                start_time=self._start_time,
                end_time=self._end_time,
                duration=duration,
                exclusive=exclusive)

        parent._children.append(node)

        self._children = []

        self._transaction._build_count += 1
        self._transaction._build_time += (time.time() - self._end_time)

class MemcacheTraceWrapper(object):

    def __init__(self, wrapped, command):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_command = command

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_command)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if not isinstance(self._nr_command, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                command = self._nr_command(*((self._nr_instance,)+args),
                                           **kwargs)
            else:
                command = self._nr_command(*args, **kwargs)
        else:
            command = self._nr_command

        with MemcacheTrace(transaction, command):
            return self._nr_next_object(*args, **kwargs)

def memcache_trace(command):
    def decorator(wrapped):
        return MemcacheTraceWrapper(wrapped, command)
    return decorator

def wrap_memcache_trace(module, object_path, command):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            MemcacheTraceWrapper, (command,))
