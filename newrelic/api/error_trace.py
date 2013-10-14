import functools
import sys

from .transaction import current_transaction
from ..common.object_wrapper import FunctionWrapper, wrap_object

class ErrorTrace(object):

    def __init__(self, transaction, ignore_errors=None):
        self._transaction = transaction
        self._ignore_errors = ignore_errors

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        if self._transaction is None:
            return

        if exc is None or value is None or tb is None:
            return

        module = value.__class__.__module__
        name = value.__class__.__name__

        # We need to check for module.name and module:name.
        # Originally we used module.class but that was
        # inconsistent with everything else which used
        # module:name. So changed to use ':' as separator, but
        # for backward compatability need to support '.' as
        # separator for time being.

        if module:
            path = '%s:%s' % (module, name)
        else:
            path = name

        if self._ignore_errors and path in self._ignore_errors:
            return

        if module:
            path = '%s.%s' % (module, name)
        else:
            path = name

        if self._ignore_errors and path in self._ignore_errors:
            return

        self._transaction.record_exception(exc, value, tb)

def ErrorTraceWrapper(wrapped, ignore_errors=None):

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        with ErrorTrace(transaction, ignore_errors):
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, wrapper)

def error_trace(ignore_errors=None):
    return functools.partial(ErrorTraceWrapper, ignore_errors=ignore_errors)

def wrap_error_trace(module, object_path, ignore_errors=None):
    wrap_object(module, object_path, ErrorTraceWrapper, (ignore_errors, ))
