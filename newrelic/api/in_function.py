import functools
import inspect

from newrelic.api.object_wrapper import ObjectWrapper, wrap_object

def InFunctionWrapper(wrapped, function):

    def wrapper(wrapped, instance, args, kwargs):
        if instance and inspect.ismethod(wrapped):
            (_args, _kwargs) = function(instance, *args, **kwargs)
            _args = _args[1:]
        else:
            (_args, _kwargs) = function(*args, **kwargs)

        return wrapped(*_args, **_kwargs)

    return ObjectWrapper(wrapped, None, wrapper)

def in_function(function):
    return functools.partial(InFunctionWrapper, function=function)

def wrap_in_function(module, object_path, function):
    return wrap_object(module, object_path, InFunctionWrapper, (function,))
