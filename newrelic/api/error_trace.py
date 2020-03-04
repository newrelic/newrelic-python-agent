import functools

from newrelic.api.time_trace import current_trace, record_exception
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object


class ErrorTrace(object):

    def __init__(self, ignore_errors=[], **kwargs):
        parent = None
        if kwargs:
            if len(kwargs) > 1:
                raise TypeError("Invalid keyword arguments:", kwargs)
            parent = kwargs['parent']

        if parent is None:
            parent = current_trace()

        self._transaction = parent and parent.transaction
        self._ignore_errors = ignore_errors

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        if exc is None or value is None or tb is None:
            return

        if self._transaction is None:
            return

        record_exception(exc=exc, value=value, tb=tb,
                ignore_errors=self._ignore_errors)


def ErrorTraceWrapper(wrapped, ignore_errors=[]):

    def wrapper(wrapped, instance, args, kwargs):
        parent = current_trace()

        if parent is None:
            return wrapped(*args, **kwargs)

        with ErrorTrace(ignore_errors, parent=parent):
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, wrapper)


def error_trace(ignore_errors=[]):
    return functools.partial(ErrorTraceWrapper, ignore_errors=ignore_errors)


def wrap_error_trace(module, object_path, ignore_errors=[]):
    wrap_object(module, object_path, ErrorTraceWrapper, (ignore_errors, ))
