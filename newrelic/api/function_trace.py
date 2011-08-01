import os
import sys
import types
import inspect

import newrelic.api.transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class FunctionTrace(object):

    def __init__(self, transaction, name=None, scope=None, interesting=True):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc, value, tb):
        pass

if _agent_mode not in ('julunggul',):
    import _newrelic
    FunctionTrace = _newrelic.FunctionTrace

class FunctionTraceWrapper(object):

    def __init__(self, wrapped, name=None, scope=None, interesting=True):
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
        self._nr_scope = scope
        self._nr_interesting = interesting

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_name,
                              self._nr_scope, self._nr_interesting)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if self._nr_name is None:
            name = newrelic.api.object_wrapper.callable_name(
                    self._nr_next_object)
        elif not isinstance(self._nr_name, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                name = self._nr_name(*((self._nr_instance,)+args), **kwargs)
            else:
                name = self._nr_name(*args, **kwargs)

        if self._nr_scope is not None and not isinstance(
                self._nr_scope, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                scope = self._nr_scope(*((self._nr_instance,)+args), **kwargs)
            else:
                scope = self._nr_scope(*args, **kwargs)
        else:
            scope = self._nr_scope

        try:
            success = True
            manager = FunctionTrace(transaction, name, scope,
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

def function_trace(name=None, scope=None, interesting=True):
    def decorator(wrapped):
        return FunctionTraceWrapper(wrapped, name, scope, interesting)
    return decorator

def wrap_function_trace(module, object_path, name=None, scope=None,
        interesting=True):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            FunctionTraceWrapper, (name, scope, interesting))

if not _agent_mode in ('ungud', 'julunggul'):
    import _newrelic
    FunctionTraceWrapper = _newrelic.FunctionTraceWrapper
    function_trace = _newrelic.function_trace
    wrap_function_trace = _newrelic.wrap_function_trace
