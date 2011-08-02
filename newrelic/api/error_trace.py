import os
import sys
import types

import newrelic.api.transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class ErrorTrace(object):

    def __init__(self, transaction, ignore_errors):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        pass

if _agent_mode not in ('julunggul',):
    import _newrelic
    ErrorTrace = _newrelic.ErrorTrace

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

if not _agent_mode in ('ungud', 'julunggul'):
    import _newrelic
    ErrorTraceWrapper = _newrelic.ErrorTraceWrapper
    error_trace = _newrelic.error_trace
    wrap_error_trace = _newrelic.wrap_error_trace
