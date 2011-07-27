import sys
import types
import inspect

import _newrelic

import newrelic.api.object_wrapper

class TraceWrapper(object):

    def __init__(self, tracer, wrapped, *args):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_tracer = tracer
        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_tracer_args = args

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), *self._nr_tracer_args)

    def tracer_args(self, *args, **kwargs):
        return self._nr_tracer_args

    def __call__(self, *args, **kwargs):
        transaction = _newrelic.transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if self._nr_instance and inspect.ismethod(self._nr_next_object):
            tracer_args = self.tracer_args((self._nr_instance,)+args, kwargs)
        else:
            tracer_args = self.tracer_args(args, kwargs)

        try:
            success = True
            manager = self._nr_tracer(transaction, *tracer_args)
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
