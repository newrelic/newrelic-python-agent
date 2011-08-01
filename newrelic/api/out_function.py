import os
import sys
import types
import inspect

import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class OutFunctionWrapper(object):

    def __init__(self, wrapped, function):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_function = function

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_function)

    def __call__(self, *args, **kwargs):
        return self._nr_function(self._nr_next_object(*args, **kwargs))

def out_function(function):
    def decorator(wrapped):
        return OutFunctionWrapper(wrapped, function)
    return decorator

def wrap_out_function(module, object_path, function):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            OutFunctionWrapper, (function, ))

if not _agent_mode in ('ungud', 'julunggul'):
    import _newrelic
    OutFunctionWrapper = _newrelic.OutFunctionWrapper
    out_function = _newrelic.out_function
    wrap_out_function = _newrelic.wrap_out_function
