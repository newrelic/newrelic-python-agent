from __future__ import with_statement

import types

import newrelic.api.in_function
import newrelic.api.function_trace
import newrelic.api.transaction
import newrelic.api.object_wrapper
import newrelic.api.error_trace
import newrelic.api.web_transaction

class ViewCallableWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor))

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.current_transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        view_callable = self._nr_next_object
        if hasattr(view_callable, '__original_view__'):
            original_view = self._nr_next_object.__original_view__
            if original_view:
                view_callable = original_view

        name = newrelic.api.object_wrapper.callable_name(view_callable)

        transaction.name_transaction(name)

        with newrelic.api.function_trace.FunctionTrace(transaction, name):
            with newrelic.api.error_trace.ErrorTrace(transaction):
                return self._nr_next_object(*args, **kwargs)

class AdaptersWrapper(object):

    def __init__(self, wrapped):
        object.__setattr__(self, '_nr_wrapped', wrapped)

    def __setattr__(self, name, value):
        setattr(self._nr_wrapped, name, value)

    def __getattr__(self, name):
        return getattr(self._nr_wrapped, name)

    def lookup(self, *args, **kwargs):
        transaction = newrelic.api.transaction.current_transaction()
        if not transaction:
            return getattr(self._nr_wrapped, 'lookup')(*args, **kwargs)
        view_callable = getattr(self._nr_wrapped, 'lookup')(*args, **kwargs)
        if view_callable is None:
            return view_callable
        return ViewCallableWrapper(view_callable)

class RegistryWrapper(object):

    def __init__(self, wrapped):
        object.__setattr__(self, '_nr_wrapped', wrapped)
        object.__setattr__(self, '_nr_called', False)

    def __setattr__(self, name, value):
        setattr(self._nr_wrapped, name, value)

    def __getattr__(self, name):
        if name == 'adapters' and not self._nr_called:
            # Don't know if need this.
            self._nr_called = True
            return AdaptersWrapper(getattr(self._nr_wrapped, name))
        return getattr(self._nr_wrapped, name)

def instrument_pyramid_router(module):

    def fixup_handle_request(*args, **kwargs):
        request = args[1]
        attrs = request.__dict__
        registry = attrs['registry']
        if not hasattr(registry, '_nr_wrapped'):
            attrs['registry'] = RegistryWrapper(registry)
        return (args, kwargs)

    newrelic.api.in_function.wrap_in_function(module,
            'Router.handle_request', fixup_handle_request)

    newrelic.api.web_transaction.wrap_wsgi_application(
            module, 'Router.__call__')
