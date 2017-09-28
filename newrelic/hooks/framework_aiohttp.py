import sys

from newrelic.api.transaction import set_background_task
from newrelic.api.background_task import BackgroundTask
from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import (wrap_function_wrapper,
        function_wrapper, ObjectProxy)
from newrelic.common.object_names import callable_name


class NRViewCoroutineWrapper(ObjectProxy):
    def __init__(self, view_name, wrapped):
        super(NRViewCoroutineWrapper, self).__init__(wrapped)
        self._nr_transaction = None
        self._nr_view_name = view_name

    def __iter__(self):
        return self

    def __await__(self):
        return self

    def __next__(self):
        return self.send(None)

    def send(self, value):
        if not self._nr_transaction:
            # create and start the transaction
            app = application_instance()
            txn = BackgroundTask(app, self._nr_view_name)
            self._nr_transaction = txn

            if txn._settings:
                txn.__enter__()
                set_background_task(False)
                txn.drop_transaction()

        txn = self._nr_transaction

        # transaction may not be active
        if not txn._settings:
            return self.__wrapped__.send(value)

        txn.save_transaction()

        try:
            r = self.__wrapped__.send(value)
            txn.drop_transaction()
            return r
        except (GeneratorExit, StopIteration):
            self._nr_transaction.__exit__(None, None, None)
            raise
        except:
            self._nr_transaction.__exit__(*sys.exc_info())
            raise

    def throw(self, *args, **kwargs):
        txn = self._nr_transaction

        # transaction may not be active
        if not txn._settings:
            return self.__wrapped__.throw(*args, **kwargs)

        txn.save_transaction()
        try:
            return self.__wrapped__.throw(*args, **kwargs)
        except:
            self._nr_transaction.__exit__(*sys.exc_info())
            raise

    def close(self):
        txn = self._nr_transaction

        # transaction may not be active
        if not txn._settings:
            return self.__wrapped__.close()

        txn.save_transaction()
        try:
            r = self.__wrapped__.close()
            self._nr_transaction.__exit__(None, None, None)
            return r
        except:
            self._nr_transaction.__exit__(*sys.exc_info())
            raise


@function_wrapper
def _nr_aiohttp_view_wrapper_(wrapped, instance, args, kwargs):
    # get the coroutine
    coro = wrapped(*args, **kwargs)

    if hasattr(coro, '__iter__'):
        coro = iter(coro)

    name = instance and callable_name(instance) or callable_name(wrapped)

    # Wrap the coroutine
    return NRViewCoroutineWrapper(name, coro)


def _nr_aiohttp_wrap_view_(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    instance._handler = _nr_aiohttp_view_wrapper_(instance._handler)
    return result


def instrument_aiohttp_web_urldispatcher(module):
    wrap_function_wrapper(module, 'ResourceRoute.__init__',
            _nr_aiohttp_wrap_view_)
