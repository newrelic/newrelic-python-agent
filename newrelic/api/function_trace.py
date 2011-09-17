import sys
import types
import inspect
import time

import newrelic.core.function_node

import newrelic.api.transaction
import newrelic.api.object_wrapper

class FunctionTrace(object):

    def __init__(self, transaction, name=None, group=None):
        self._transaction = transaction

        self._name = name
        self._group = group

        self._enabled = False

        self._children = []

        self._start_time = 0.0
        self._end_time = 0.0

    def __enter__(self):
        if not self._transaction.active:
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

        group = self._group

        if group is None:
            group = 'Function'

        node = newrelic.core.function_node.FunctionNode(
                group=group,
                name=self._name,
                children=self._children,
                start_time=self._start_time,
                end_time=self._end_time,
                duration=duration,
                exclusive=exclusive)

        parent._children.append(node)

        self._children = []

        self._transaction._build_count += 1
        self._transaction._build_time += (time.time() - self._end_time)

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
        if not transaction or not transaction.active:
            return self._nr_next_object(*args, **kwargs)

        if self._nr_name is None:
            name = newrelic.api.object_wrapper.callable_name(
                    self._nr_next_object)
        elif not isinstance(self._nr_name, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                name = self._nr_name(*((self._nr_instance,)+args), **kwargs)
            else:
                name = self._nr_name(*args, **kwargs)
        else:
            name = self._nr_name

        if self._nr_group is not None and not isinstance(
                self._nr_group, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                group = self._nr_group(*((self._nr_instance,)+args), **kwargs)
            else:
                group = self._nr_group(*args, **kwargs)
        else:
            group = self._nr_group

        try:
            success = True
            manager = FunctionTrace(transaction, name, group,
                                    self._nr_interesting)
            manager.__enter__()
            try:
                return self._nr_next_object(*args, **kwargs)
            except:
                success = False
                if not manager.__exit__(*sys.exc_info()):
                    raise
        finally:
            if success:
                manager.__exit__(None, None, None)

        #with FunctionTrace(transaction, name, group, self._nr_interesting):
        #    return self._nr_next_object(*args, **kwargs)

        with FunctionTrace(transaction, name, group):
            return self._nr_next_object(*args, **kwargs)

def function_trace(name=None, group=None):
    def decorator(wrapped):
        return FunctionTraceWrapper(wrapped, name, group)
    return decorator

def wrap_function_trace(module, object_path, name=None, group=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            FunctionTraceWrapper, (name, group))
