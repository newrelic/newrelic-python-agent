import sys
import types
import inspect

import newrelic.api.transaction
import newrelic.api.web_transaction
import newrelic.api.object_wrapper

class BackgroundTask(newrelic.api.transaction.Transaction):

    def __init__(self, application, name, group=None):

        # Initialise the common transaction base class.

        newrelic.api.transaction.Transaction.__init__(self, application)

        # Mark this as a background task even if disabled.

        self.background_task = True

        # Bail out if the transaction is running in a
        # disabled state.

        if not self.enabled:
            return

        # Name the web transaction from supplied values.

        self.name_transaction(name, group, priority=1)

class xBackgroundTaskWrapper(object):

    def __init__(self, wrapped, application=None, name=None, group=None):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_application = application
        self._nr_name = name
        self._nr_group = group

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_application,
                              self._nr_name, self._nr_group)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()

        if self._nr_name is None:
            name = newrelic.api.object_wrapper.callable_name(
                    self._nr_next_object)
        elif not isinstance(self._nr_name, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                name = self._nr_name(self._nr_instance, *args, **kwargs)
            else:
                name = self._nr_name(*args, **kwargs)
        else:
            name = self._nr_name

        if self._nr_group is not None and not isinstance(
                self._nr_group, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                group = self._nr_group(self._nr_instance, *args, **kwargs)
            else:
                group = self._nr_group(*args, **kwargs)
        else:
            group = self._nr_group

        # Check to see if we are being called within the context
        # of a web transaction. If we are, then we will just
        # flag the current web transaction as a background task
        # if not already marked as such and name the web
        # transaction as well. In any case, if nested in another
        # transaction be it a web transaction or background
        # task, then we don't do anything else and just called
        # the wrapped function.

        if transaction:
            if (type(transaction) ==
                    newrelic.api.web_transaction.WebTransaction):

                if not transaction.background_task:
                    transaction.background_task = True
                    transaction.name_transaction(name, group)

            return self._nr_next_object(*args, **kwargs)

        # Otherwise treat it as top level transaction.

        application = self._nr_application
        if type(application) != newrelic.api.application.Application:
            application = newrelic.api.application.application(application)

        try:
            success = True
            manager = BackgroundTask(application, name, group)
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

class BackgroundTaskWrapper(newrelic.api.object_wrapper.ObjectWrapper):

    def __init__(self, wrapped, application=None, name=None, group=None):
        super(BackgroundTaskWrapper, self).__init__(wrapped)

        self._nr_application = application
        self._nr_name = name
        self._nr_group = group

    def _nr_new_object(self, wrapped):
        return self.__class__(wrapped, self._nr_application,
                              self._nr_name, self._nr_group)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()

        if self._nr_name is None:
            name = newrelic.api.object_wrapper.callable_name(
                    self._nr_next_object)
        elif not isinstance(self._nr_name, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                name = self._nr_name(self._nr_instance, *args, **kwargs)
            else:
                name = self._nr_name(*args, **kwargs)
        else:
            name = self._nr_name

        if self._nr_group is not None and not isinstance(
                self._nr_group, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                group = self._nr_group(self._nr_instance, *args, **kwargs)
            else:
                group = self._nr_group(*args, **kwargs)
        else:
            group = self._nr_group

        # Check to see if we are being called within the context
        # of a web transaction. If we are, then we will just
        # flag the current web transaction as a background task
        # if not already marked as such and name the web
        # transaction as well. In any case, if nested in another
        # transaction be it a web transaction or background
        # task, then we don't do anything else and just called
        # the wrapped function.

        if transaction:
            if (type(transaction) ==
                    newrelic.api.web_transaction.WebTransaction):

                if not transaction.background_task:
                    transaction.background_task = True
                    transaction.name_transaction(name, group)

            return self._nr_next_object(*args, **kwargs)

        # Otherwise treat it as top level transaction.

        application = self._nr_application
        if type(application) != newrelic.api.application.Application:
            application = newrelic.api.application.application(application)

        try:
            success = True
            manager = BackgroundTask(application, name, group)
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

def background_task(application=None, name=None, group=None):
    def decorator(wrapped):
        return BackgroundTaskWrapper(wrapped, application, name, group)
    return decorator

def wrap_background_task(module, object_path, application=None, name=None,
                         group=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            BackgroundTaskWrapper, (application, name, group))
