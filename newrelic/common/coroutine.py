import inspect
import newrelic.packages.six as six


if hasattr(inspect, 'iscoroutinefunction'):
    def is_coroutine_function(wrapped):
        return inspect.iscoroutinefunction(wrapped)
else:
    def is_coroutine_function(wrapped):
        return False


if six.PY3:
    def is_asyncio_coroutine(wrapped):
        """Return True if func is a decorated coroutine function."""
        return getattr(wrapped, '_is_coroutine', None) is not None
else:
    def is_asyncio_coroutine(wrapped):
        return False


def is_generator_function(wrapped):
    return inspect.isgeneratorfunction(wrapped)


def _iscoroutinefunction_tornado(fn):
    return hasattr(fn, '__tornado_coroutine__')
