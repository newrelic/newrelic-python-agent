# vi: set sw=4 expandtab :

__all__ = [ 'background_task', 'function_trace', 'external_trace',
            'memcache_trace', 'database_trace' ]

import inspect
import types

import _newrelic

# Function for introspecting the name of the module, class and
# the callable being wrapped by a decorator. Note that this does
# not provide the desired result if applied to the as yet
# unbound function of a class as Python doesn't provide a way of
# determining the class the function is to be bound to within a
# decorator itself. Instead, would be necessary to use special
# purpose decorators for class methods which looks at the class
# associated with the first argument of the function when
# called, ie., the 'self' argument.

def _qualified_name(object):
    mname = inspect.getmodule(object).__name__

    cname = None
    fname = None

    if inspect.isclass(object):
        cname = object.__name__
        fname = '__init__'
    elif inspect.ismethod(object):
        cname = object.im_class.__name__
        fname = object.__name__
    elif inspect.isfunction(object):
        fname = object.__name__
    elif isinstance(object, types.InstanceType):
        cname = object.__class__.__name__
        fname = '__call__'
    elif hasattr(object, '__class__'):
        cname = object.__class__.__name__
        fname = '__call__'

    path = mname

    if cname:
        path += '.'
        path += cname

    if fname:
        path += '::'
        path += fname

    return path

# Provide decorator for background task. This is just a special
# class of web transaction marked as a background task.

def background_task(name=None):
    application = _newrelic.application(name)

    def decorator(callable):

        def wrapper(*args, **kwargs):

	    # When a decorator is used on a class method, it
	    # isn't bound to a class instance at the time and so
	    # within the decorator we are not able to determine
	    # the class. To work out the class we need to look
	    # at the class associated with the first argument,
	    # ie., self argument passed to the method. Because
	    # though we don't know if we are even being called
	    # as a class method we have to do an elaborate check
	    # whereby we see if the first argument is a class
	    # instance possessing a bound method which the
	    # associated function is our wrapper function.

            qualified_name = name

            if not qualified_name and inspect.isfunction(callable):
                if len(args) >= 1 and hasattr(args[0], '__class__'):
                    klass = args[0].__class__
                    if hasattr(klass, callable.__name__):
                        method = getattr(klass, callable.__name__)
                        if inspect.ismethod(method):
                            if method.im_func == wrapper:
                                qualified_name = _qualified_name(method)

            path = qualified_name or _qualified_name(callable)

            transaction = _newrelic.BackgroundTask(application, path)

            transaction.__enter__()

            try:
                return callable(*args, **kwargs)
            except:
                transaction.__exit__(*sys.exc_info())
            else:
                transaction.__exit__(None, None, None)

	# Associate the name of the wrapped callable with our
	# wrapper to make it easier to construct the qualified
	# name using same routine as original callable object.

        wrapper.__name__ = getattr(callable, '__name__', wrapper.__name__)
        wrapper.__doc__ = getattr(callable, '__doc__', None)

        return wrapper

    return decorator


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

def function_trace(name=None, scope=None, override_path=False):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            transaction = _newrelic.transaction()
            if not transaction:
                return callable(*args, **kwargs)

	    # When a decorator is used on a class method, it
	    # isn't bound to a class instance at the time and so
	    # within the decorator we are not able to determine
	    # the class. To work out the class we need to look
	    # at the class associated with the first argument,
	    # ie., self argument passed to the method. Because
	    # though we don't know if we are even being called
	    # as a class method we have to do an elaborate check
	    # whereby we see if the first argument is a class
	    # instance possessing a bound method which the
	    # associated function is our wrapper function.

            qualified_name = name

            if not qualified_name and inspect.isfunction(callable):
                if len(args) >= 1 and hasattr(args[0], '__class__'):
                    klass = args[0].__class__
                    if hasattr(klass, callable.__name__):
                        method = getattr(klass, callable.__name__)
                        if inspect.ismethod(method):
                            if method.im_func == wrapper:
                                qualified_name = _qualified_name(method)

            qualified_name = qualified_name or _qualified_name(callable)

            if override_path:
                transaction.path = qualified_name

            trace = _newrelic.FunctionTrace(transaction, qualified_name,
                                            None, scope)
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

	# Associate the name of the wrapped callable with our
	# wrapper to make it easier to construct the qualified
	# name using same routine as original callable object.

        wrapper.__name__ = getattr(callable, '__name__', wrapper.__name__)
        wrapper.__doc__ = getattr(callable, '__doc__', None)

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

        wrapper.__name__ = getattr(callable, '__name__', wrapper.__name__)
        wrapper.__doc__ = getattr(callable, '__doc__', None)

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

        wrapper.__name__ = getattr(callable, '__name__', wrapper.__name__)
        wrapper.__doc__ = getattr(callable, '__doc__', None)

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

        wrapper.__name__ = getattr(callable, '__name__', wrapper.__name__)
        wrapper.__doc__ = getattr(callable, '__doc__', None)

        return wrapper

    return decorator
