from newrelic.api.object_wrapper import ObjectWrapper, wrap_object

def OutFunctionWrapper(wrapped, function):

    def wrapper(wrapped, instance, args, kwargs):
        return function(wrapped(*args, **kwargs))

    return ObjectWrapper(wrapped, None, wrapper)

def out_function(function):
    def decorator(wrapped):
        return OutFunctionWrapper(wrapped, function)
    return decorator

def wrap_out_function(module, object_path, function):
    return wrap_object(module, object_path, OutFunctionWrapper, (function, ))
