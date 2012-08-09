import functools
import inspect

from newrelic.api.object_wrapper import ObjectWrapper, wrap_object

def PreFunctionWrapper(wrapped, function):

    def wrapper(wrapped, instance, args, kwargs):
        if instance and inspect.ismethod(wrapped):
            function(instance, *args, **kwargs)
        else:
            function(*args, **kwargs)

        return wrapped(*args, **kwargs)

    return ObjectWrapper(wrapped, None, wrapper)

def pre_function(function):
    return functools.partial(PreFunctionWrapper, function=function)

def wrap_pre_function(module, object_path, function):
    return wrap_object(module, object_path, PreFunctionWrapper, (function,))
