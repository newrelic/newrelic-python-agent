import functools
import sys

from .application import Application, application_instance
from .transaction import Transaction, current_transaction
from .web_transaction import WebTransaction
from ..common.object_wrapper import FunctionWrapper, wrap_object
from ..common.object_names import callable_name

class BackgroundTask(Transaction):

    def __init__(self, application, name, group=None):

        # Initialise the common transaction base class.

        super(BackgroundTask, self).__init__(application)

        # Mark this as a background task even if disabled.

        self.background_task = True

        # Bail out if the transaction is running in a
        # disabled state.

        if not self.enabled:
            return

        # Name the web transaction from supplied values.

        self.set_transaction_name(name, group, priority=1)

def BackgroundTaskWrapper(wrapped, application=None, name=None, group=None):

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if callable(name):
            if instance is not None:
                _name = name(instance, *args, **kwargs)
            else:
                _name = name(*args, **kwargs)

        elif name is None:
            _name = callable_name(wrapped)

        else:
            _name = name

        if callable(group):
            if instance is not None:
                _group = group(instance, *args, **kwargs)
            else:
                _group = group(*args, **kwargs)

        else:
            _group = group

        # Check to see if we are being called within the context
        # of a web transaction. If we are, then we will just
        # flag the current web transaction as a background task
        # if not already marked as such and name the web
        # transaction as well. In any case, if nested in another
        # transaction be it a web transaction or background
        # task, then we don't do anything else and just called
        # the wrapped function.

        if transaction:
            if type(transaction) == WebTransaction:
                if not transaction.background_task:
                    transaction.background_task = True
                    transaction.set_transaction_name(_name, _group)

            return wrapped(*args, **kwargs)

        # Otherwise treat it as top level transaction.

        if type(application) != Application:
            _application = application_instance(application)
        else:
            _application = application

        try:
            success = True
            manager = BackgroundTask(_application, _name, _group)
            manager.__enter__()
            try:
                return wrapped(*args, **kwargs)
            except: #  Catch all
                success = False
                if not manager.__exit__(*sys.exc_info()):
                    raise
        finally:
            if success:
                manager.__exit__(None, None, None)

    return FunctionWrapper(wrapped, wrapper)

def background_task(application=None, name=None, group=None):
    return functools.partial(BackgroundTaskWrapper,
            application=application, name=name, group=group)

def wrap_background_task(module, object_path, application=None,
        name=None, group=None):
    wrap_object(module, object_path, BackgroundTaskWrapper,
            (application, name, group))
