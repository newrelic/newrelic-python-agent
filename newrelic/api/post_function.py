import functools
import inspect

from newrelic.api.object_wrapper import ObjectWrapper, wrap_object

def PostFunctionWrapper(wrapped, function):

    def wrapper(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        if instance and inspect.ismethod(wrapped):
            function(instance, *args, **kwargs)
        else:
            function(*args, **kwargs)

        return result

    return ObjectWrapper(wrapped, None, wrapper)

def post_function(function):
    return functools.partial(PostFunctionWrapper, function=function)

def wrap_post_function(module, object_path, function):
    return wrap_object(module, object_path, PostFunctionWrapper, (function,))
