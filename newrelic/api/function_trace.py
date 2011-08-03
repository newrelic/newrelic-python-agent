import os
import sys
import types
import inspect
import time
import collections

import newrelic.api.transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

FunctionNode = collections.namedtuple('FunctionNode',
        ['name', 'children', 'start_time', 'end_time'])

class FunctionTrace(object):

    def __init__(self, transaction, name=None, group=None, interesting=True):
        self._transaction = transaction

        self._name = name
        self._group = group

        self._interesting = interesting

        self._enabled = False

        self._children = []

        self._start_time = 0.0
        self._end_time = 0.0

    def __enter__(self):
        if not self._transaction.active:
            return

        self._enabled = True

        self._start_time = time.time()

        self._transaction._node_stack.append(self)

        return self

    def __exit__(self, exc, value, tb):
        if not self._enabled:
            return

        self._end_time = time.time()

        node = self._transaction._node_stack.pop()
        assert(node == self)

        parent = self._transaction._node_stack[-1]

        if self._group:
            name = '%s/%s' % (self._group, self._name)
        else:
            name = self._name

        parent._children.append(FunctionNode(name=name,
                children=self._children, start_time=self._start_time,
                end_time=self._end_time))

        self._children = []

if _agent_mode not in ('julunggul',):
    import _newrelic
    FunctionTrace = _newrelic.FunctionTrace

class FunctionTraceWrapper(object):

    def __init__(self, wrapped, name=None, group=None, interesting=True):
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
        self._nr_interesting = interesting

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_name,
                              self._nr_group, self._nr_interesting)

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

def function_trace(name=None, group=None, interesting=True):
    def decorator(wrapped):
        return FunctionTraceWrapper(wrapped, name, group, interesting)
    return decorator

def wrap_function_trace(module, object_path, name=None, group=None,
        interesting=True):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            FunctionTraceWrapper, (name, group, interesting))

if not _agent_mode in ('ungud', 'julunggul'):
    import _newrelic
    FunctionTraceWrapper = _newrelic.FunctionTraceWrapper
    function_trace = _newrelic.function_trace
    wrap_function_trace = _newrelic.wrap_function_trace
