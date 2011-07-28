import os
import sys
import types
import inspect

import _newrelic

import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class InFunctionWrapper(object):

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
        (wrapped_args, wrapped_kwargs) = self._nr_function(*args, **kwargs)
        return self._nr_next_object(*wrapped_args, **wrapped_kwargs)

def in_function(function):
    def decorator(wrapped):
        return InFunctionWrapper(wrapped, function)
    return decorator

def wrap_in_function(module, object_path, function):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            InFunctionWrapper, (function, ))

if not _agent_mode in ('ungud', 'julunggul'):
    InFunctionWrapper = _newrelic.InFunctionWrapper
    in_function = _newrelic.in_function
    wrap_in_function = _newrelic.wrap_in_function
