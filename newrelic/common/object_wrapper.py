"""This module implements a generic object wrapper for use in performing
monkey patching, helper functions to perform monkey patching and general
purpose decorators and wrapper functions for various basic tasks one can
make use of when doing monkey patching.

"""

import sys
import inspect
import functools

from ..packages.wrapt import ObjectProxy, FunctionWrapper
from ..packages.wrapt.wrappers import (_FunctionWrapperBase,
        _BoundFunctionWrapper, _BoundMethodWrapper)

# We previously had our own pure Python implementation of the generic
# object wrapper but we now defer to using the wrapt module as its C
# implementation has less than ten percent of the overhead for the common
# case of instance methods. Even the wrapt pure Python implementation
# of wrapt has about fifty percent of the overhead. The wrapt module
# implementation is also much more comprehensive as far as being a
# transparent object proxy. The only problem is that until we can cut
# over completely to a generic API, we need to maintain the existing API
# we used. This requires the fiddles below where we need to customise by
# what names everything is accessed. Note that with the code below, the
# _ObjectWrapperBase class must come first in the base class list of
# the derived class to ensure correct precedence order on base class
# method lookup for __setattr__(), __getattr__() and __delattr__().

class _ObjectWrapperBase(object):

    def __setattr__(self, name, value):
        if name.startswith('_nr_'):
            name = name.replace('_nr_', '_self_', 1)
            setattr(self, name, value)
        else:
            ObjectProxy.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name.startswith('_nr_'):
            name = name.replace('_nr_', '_self_', 1)
            return getattr(self, name)
        else:
            return ObjectProxy.__getattr__(self, name)

    def __delattr__(self, name):
        if name.startswith('_nr_'):
            name = name.replace('_nr_', '_self_', 1)
            delattr(self, name)
        else:
            ObjectProxy.__delattr__(self, name)

    @property
    def _nr_next_object(self):
        return self.__wrapped__

    @property
    def _nr_last_object(self):
        try:
            return self._self_last_object
        except AttributeError:
            self._self_last_object = getattr(self.__wrapped__,
                    '_nr_last_object', self.__wrapped__)
            return self._self_last_object

    @property
    def _nr_instance(self):
        return self._self_instance

    @property
    def _nr_wrapper(self):
        return self._self_wrapper

    @property
    def _nr_parent(self):
        return self._self_parent

class _NRBoundFunctionWrapper(_ObjectWrapperBase, _BoundFunctionWrapper):
    pass

class _NRBoundMethodWrapper(_ObjectWrapperBase, _BoundMethodWrapper):
    pass

class ObjectWrapper(_ObjectWrapperBase, _FunctionWrapperBase):

    def __init__(self, wrapped, instance, wrapper):
        if isinstance(wrapped, (classmethod, staticmethod)):
            bound_type = _NRBoundFunctionWrapper
        else:
            bound_type = _NRBoundMethodWrapper

        super(ObjectWrapper, self).__init__(wrapped, instance, wrapper,
                None, bound_type)

# Helper functions for performing monkey patching.

def resolve_path(module, name):
    if not inspect.ismodule(module):
        __import__(module)
        module = sys.modules[module]

    parent = module

    path = name.split('.')
    attribute = path[0]

    original = getattr(parent, attribute)
    for attribute in path[1:]:
        parent = original
        original = getattr(original, attribute)

    return (parent, attribute, original)

def apply_patch(parent, attribute, replacement):
    setattr(parent, attribute, replacement)

def wrap_object(module, name, factory, args=(), kwargs={}):
    (parent, attribute, original) = resolve_path(module, name)
    wrapper = factory(original, *args, **kwargs)
    apply_patch(parent, attribute, wrapper)
    return wrapper

def wrap_callable(wrapped, wrapper):
    return ObjectWrapper(wrapped, None, wrapper)

# Decorator for creating decorators using our ObjectWrapper. Later on
# when we have made ObjectWrapper obsolete, we can change this so we use
# the decorator for creating decorators in the wrapt module.

def decorator(wrapper):
    @functools.wraps(wrapper)
    def _wrapper(wrapped):
        return ObjectWrapper(wrapped, None, wrapper)
    return _wrapper

# Decorator for creating a decorator wrapper and immediately using it
# to monkey match the specified code.

def patch_object(module, name):
    def _wrapper(wrapper):
        return wrap_object(module, name, ObjectWrapper, (None, wrapper))
    return _wrapper

# Generic decorators for performing actions before and after a wrapped
# function is called, or modifying the inbound arguments or return value.

def pre_function(function):
    @decorator
    def _wrapper(wrapped, instance, args, kwargs):
        if instance is not None:
            function(instance, *args, **kwargs)
        else:
            function(*args, **kwargs)
        return wrapped(*args, **kwargs)
    return _wrapper

def PreFunctionWrapper(wrapped, function):
    return pre_function(function)(wrapped)

def wrap_pre_function(module, object_path, function):
    return wrap_object(module, object_path, PreFunctionWrapper, (function,))

def post_function(function):
    @decorator
    def _wrapper(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)
        if instance is not None:
            function(instance, *args, **kwargs)
        else:
            function(*args, **kwargs)
        return result
    return _wrapper

def PostFunctionWrapper(wrapped, function):
    return post_function(function)(wrapped)

def wrap_post_function(module, object_path, function):
    return wrap_object(module, object_path, PostFunctionWrapper, (function,))

def in_function(function):
    @decorator
    def _wrapper(wrapped, instance, args, kwargs):
        if instance is not None:
            args, kwargs = function(instance, *args, **kwargs)

            # The instance is passed into the supplied function and for
            # consistency it is also expected to also be returned
            # otherwise it gets fiddly for the supplied function to
            # remove it. It is expected that the instance returned in
            # the arguments is the same value as it is simply dropped
            # after being returned. This is necessary as the instance is
            # not passed through anyway in arguments to the wrapped
            # function, as the instance is already bound to the wrapped
            # function at this point and supplied automatically.

            return wrapped(*args[1:], **kwargs)

        args, kwargs = function(*args, **kwargs)
        return wrapped(*args, **kwargs)

    return _wrapper

def InFunctionWrapper(wrapped, function):
    return in_function(function)(wrapped)

def wrap_in_function(module, object_path, function):
    return wrap_object(module, object_path, InFunctionWrapper, (function,))

def out_function(function):
    @decorator
    def _wrapper(wrapped, instance, args, kwargs):
        return function(wrapped(*args, **kwargs))
    return _wrapper

def OutFunctionWrapper(wrapped, function):
    return out_function(function)(wrapped)

def wrap_out_function(module, object_path, function):
    return wrap_object(module, object_path, OutFunctionWrapper, (function,))
