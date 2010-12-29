# vi: set sw=4 expandtab :

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

def web_transaction(name):
    application = applications.Application(name)

    def decorator(callable):
        return middleware.WebTransaction(application, callable)

    return decorator

def _qualified_name(callable):
    if hasattr(callable, 'im_class'):
        return '%s:%s.%s' % (callable.im_class.__module__,
                callable.im_class.__name__, callable.__name__)
    elif hasattr(callable, '__module__'):
        return '%s:%s' % (callable.__module__, callable.__name__)
    else:
        return callable.__name__

def function_trace(name=None, override_path=False):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            try:
                transaction = middleware.current_transaction()
            except:
                return callable(*args, **kwargs)

            qualified_name = name or _qualified_name(callable)

            if override_path:
                transaction.path = qualified_name

            trace = transaction.function_trace(qualified_name)
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
            try:
                transaction = middleware.current_transaction()
            except:
                return callable(*args, **kwargs)

            trace = transaction.external_trace(args[index])
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
            try:
                transaction = middleware.current_transaction()
            except:
                return callable(*args, **kwargs)

            trace = transaction.memcache_trace(args[index])
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
            try:
                transaction = middleware.current_transaction()
            except:
                return callable(*args, **kwargs)

            trace = transaction.database_trace(args[index])
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

        return wrapper

    return decorator
