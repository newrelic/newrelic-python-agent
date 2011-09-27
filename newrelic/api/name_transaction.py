import types
import inspect

import newrelic.api.transaction
import newrelic.api.object_wrapper

class NameTransactionWrapper(object):

    def __init__(self, wrapped, name=None, group=None, priority=None):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_name = name
        self._nr_group = group
        self._nr_priority = priority

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor),
                self._nr_name, self._nr_group, self._nr_priority)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if self._nr_instance and inspect.ismethod(self._nr_next_object):
            fnargs = (self._nr_instance,)+args
        else:
            fnargs = args

        if self._nr_name is None:
            name = newrelic.api.object_wrapper.callable_name(
                    self._nr_next_object)
        elif not isinstance(self._nr_name, basestring):
            name = self._nr_name(*fnargs, **kwargs)

        if self._nr_group is not None and not isinstance(
                self._nr_group, basestring):
            group = self.nr_group(*fnargs, **kwargs)
        else:
            group = self._nr_group

        transaction.name_transaction(name, group, self._nr_priority)

        return self._nr_next_object(*args, **kwargs)

def name_transaction(name=None, group=None, priority=None):
    def decorator(wrapped):
        return NameTransactionWrapper(wrapped, name, group, priority)
    return decorator

def wrap_name_transaction(module, object_path, name=None, group=None,
                          priority=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            NameTransactionWrapper, (name, group, priority))
