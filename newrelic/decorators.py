# vi: set sw=4 expandtab :

import inspect
import types

import _newrelic

import applications
import middleware

# Provide decorators for transaction traces which ensure sub
# timing is started and stopped appropriatey in all situations.
# When the wrapped function is called outside of the context of
# a transaction the call will proceed but no metrics recorded.
#
# When applied to class methods they should be applied to the
# class method definition and not restrospectively to the
# bound method of an existing class. If the latter is done, the
# name of the class will not be reported properly in the path
# of a web transaction if the name of bound method is to be
# used to override the path of the web transaction.
#
# Note that these stop timing on exit from the wrapped callable.
# If the result is a generator which is then consumed in outer
# scope, that consumption doesn't count towards the time.

def wsgi_application(name):
    application = _newrelic.application(name)

    def decorator(callable):
        return middleware.WSGIApplication(application, callable)

    return decorator

def _qualified_name(object):
    mname = inspect.getmodule(object).__name__

    if inspect.isclass(object):
        cname = object.__name__
    elif hasattr(object, 'im_class'):
        cname = object.im_class.__name__
    elif isinstance(object, types.InstanceType):
        cname = object.__class__.__name__
    elif hasattr(object, '__class__'):
        cname = object.__class__.__name__
    else:
        cname = None

    if inspect.isfunction(object):
        fname = object.__name__
    elif inspect.ismethod(object):
        fname = object.__name__
    elif isinstance(object, types.TypeType):
        fname = None
    elif hasattr(object, '__call__'):
        fname = '__call__'
    else:
        fname = None

    path = mname

    if cname:
        path += '.'
        path += cname

    if fname:
        path += '::'
        path += fname

    return path

def function_trace(name=None, scope=None, override_path=False):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            transaction = _newrelic.transaction()
            if not transaction:
                return callable(*args, **kwargs)

            qualified_name = name or _qualified_name(callable)

            print scope, callable, qualified_name

            if override_path:
                transaction.path = qualified_name

            trace = _newrelic.FunctionTrace(transaction, qualified_name,
                                            None, scope)
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

        return wrapper

    return decorator

def external_trace(index):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            transaction = _newrelic.transaction()
            if not transaction:
                return callable(*args, **kwargs)

            trace = _newrelic.ExternalTrace(transaction, args[index])
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

        return wrapper

    return decorator

def memcache_trace(index):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            transaction = _newrelic.transaction()
            if not transaction:
                return callable(*args, **kwargs)

            trace = _newrelic.MemcacheTrace(transaction, args[index])
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

        return wrapper

    return decorator

def database_trace(index):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            transaction = _newrelic.transaction()
            if not transaction:
                return callable(*args, **kwargs)

            trace = _newrelic.DatabaseTrace(transaction, args[index])
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

        return wrapper

    return decorator
