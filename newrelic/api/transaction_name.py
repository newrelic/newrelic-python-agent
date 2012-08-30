import functools
import inspect

from newrelic.api.transaction import current_transaction
from newrelic.api.object_wrapper import (ObjectWrapper,
        callable_name, wrap_object)

def TransactionNameWrapper(wrapped, name=None, group=None, priority=None):

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(name):
            if instance and inspect.ismethod(wrapped):
                _name = name(instance, *args, **kwargs)
            else:
                _name = name(*args, **kwargs)

        elif name is None:
            _name = callable_name(wrapped)

        else:
            _name = name

        if callable(group):
            if instance and inspect.ismethod(wrapped):
                _group = group(instance, *args, **kwargs)
            else:
                _group = group(*args, **kwargs)

        else:
            _group = group

        transaction.name_transaction(_name, _group, priority)

        return wrapped(*args, **kwargs)

    def literal_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        _name = name or callable_name(wrapped)

        transaction.name_transaction(_name, group, priority)

        return wrapped(*args, **kwargs)

    if callable(name) or callable(group):
        return ObjectWrapper(wrapped, None, dynamic_wrapper)

    return ObjectWrapper(wrapped, None, literal_wrapper)

def transaction_name(name=None, group=None, priority=None):
    return functools.partial(TransactionNameWrapper, name=name,
            group=group, priority=priority)

def wrap_transaction_name(module, object_path, name=None, group=None,
                          priority=None):
    return wrap_object(module, object_path, TransactionNameWrapper,
            (name, group, priority))
