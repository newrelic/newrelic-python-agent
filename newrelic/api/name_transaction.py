import os
import types
import inspect

import newrelic.api.transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class NameTransactionWrapper(object):

    def __init__(self, wrapped, name=None, scope=None):
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
        self._nr_scope = scope

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor),
                self._nr_name, self._nr_scope)

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

        if self._nr_scope is not None and not isinstance(
                self._nr_scope, basestring):
            scope = self.nr_scope(*fnargs, **kwargs)
        else:
            scope = self._nr_scope

        transaction.name_transaction(name, scope)

        return self._nr_next_object(*args, **kwargs)

def name_transaction(name=None, scope=None):
    def decorator(wrapped):
        return NameTransactionWrapper(wrapped, name, scope)
    return decorator

def wrap_name_transaction(module, object_path, name=None, scope=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            NameTransactionWrapper, (name, scope))

if not _agent_mode in ('ungud', 'julunggul'):
    import _newrelic
    NameTransactionWrapper = _newrelic.NameTransactionWrapper
    name_transaction = _newrelic.name_transaction
    wrap_name_transaction = _newrelic.wrap_name_transaction
