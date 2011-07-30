import os
import sys
import types
import inspect

import _newrelic

import newrelic.api.transaction
import newrelic.api.web_transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

BackgroundTask = _newrelic.BackgroundTask

class BackgroundTaskWrapper(object):

    def __init__(self, wrapped, application=None, name=None, scope=None):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        if type(application) != newrelic.api.application.Application:
            application = newrelic.api.application.application(application)

        self._nr_application = application
        self._nr_name = name
        self._nr_scope = scope

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_application,
                              self._nr_name, self._nr_scope)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()

        if self._nr_name is None:
            name = newrelic.api.object_wrapper.callable_name(
                    self._nr_next_object)
        elif not isinstance(self._nr_name, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                name = self._nr_name(*((self._nr_instance,)+args), **kwargs)
            else:
                name = self._nr_name(*args, **kwargs)

        if self._nr_scope is not None and not isinstance(
                self._nr_scope, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                scope = self._nr_scope(*((self._nr_instance,)+args), **kwargs)
            else:
                scope = self._nr_scope(*args, **kwargs)
        else:
            scope = self._nr_scope

	# Check to see if we are being called within the context
	# of a web transaction. If we are, then rather than
	# start a new transaction for a background task, we will
	# just flag the current web transaction as a background
	# task. If nested in another background task, then we
        # don't do anything and just called the wrapped function.

        if transaction:
            if (type(transaction) ==
                    newrelic.api.web_transaction.WebTransaction):

                transaction.background_task = True
                transaction.name_transaction(name, scope)

            return self._nr_next_object(*args, **kwargs)

        # Otherwise treat it as top level transaction.

        try:
            success = True
            manager = BackgroundTask(application, name, scope)
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

def background_task(application=None, name=None, scope=None):
    def decorator(wrapped):
        return BackgroundTaskWrapper(wrapped, application, name, scope)
    return decorator

def wrap_background_task(module, object_path, application=None, name=None,
                         scope=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            BackgroundTaskWrapper, (application, name, scope))

if not _agent_mode in ('ungud', 'julunggul'):
    background_task = _newrelic.background_task
    wrap_background_task = _newrelic.wrap_background_task
    BackgroundTaskWrapper = _newrelic.BackgroundTaskWrapper
