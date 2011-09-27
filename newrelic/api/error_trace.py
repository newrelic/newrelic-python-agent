import sys
import types

import newrelic.api.transaction
import newrelic.api.object_wrapper

class ErrorTrace(object):

    def __init__(self, transaction, ignore_errors=None):
        assert transaction is not None

        self._transaction = transaction
        self._ignore_errors = ignore_errors

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        if exc is None or value is None or tb is None:
            return

        module = value.__class__.__module__
        name = value.__class__.__name__

        if module:
            path = '%s.%s' % (module, name)
        else:
            path = name

        if self._ignore_errors and path in self._ignore_errors:
            return

        self._transaction.notice_error(exc, value, tb)

class ErrorTraceWrapper(object):

    def __init__(self, wrapped, ignore_errors=None):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_ignore_errors = ignore_errors

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_ignore_errors)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        try:
            success = True
            manager = ErrorTrace(transaction, self._nr_ignore_errors)
            manager.__enter__()
            try:
                return self._nr_next_object(*args, **kwargs)
            except:
                success = False
                if not manager.__exit__(*sys.exc_info()):
                    raise
        finally:
            if success:
                manager.__exit__(None, None, None)

def error_trace(ignore_errors=None):
    def decorator(wrapped):
        return ErrorTraceWrapper(wrapped, ignore_errors)
    return decorator

def wrap_error_trace(module, object_path, ignore_errors=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            ErrorTraceWrapper, (ignore_errors, ))
