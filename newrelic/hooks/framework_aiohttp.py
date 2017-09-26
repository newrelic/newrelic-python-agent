import sys

from newrelic.api.transaction import set_background_task
from newrelic.api.background_task import BackgroundTask
from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import (wrap_function_wrapper,
        function_wrapper)
from newrelic.common.object_names import callable_name
from asyncio.coroutines import CoroWrapper


class NRViewCoroutineWrapper(CoroWrapper):
    def __init__(self, view_name, gen, func=None):
        super(NRViewCoroutineWrapper, self).__init__(gen, func)
        self.transaction = None
        self.view_name = view_name

    def __next__(self):
        if not self.transaction:
            # create and start the transaction
            app = application_instance()
            txn = BackgroundTask(app, self.view_name)
            self.transaction = txn

            if txn._settings:
                txn.__enter__()
                set_background_task(False)
                txn.drop_transaction()

        txn = self.transaction

        # transaction may not be active
        if not txn._settings:
            return self.gen.send(None)

        txn.save_transaction()

        try:
            r = self.gen.send(None)
            txn.drop_transaction()
            return r
        except (GeneratorExit, StopIteration):
            self.transaction.__exit__(None, None, None)
            raise
        except:
            self.transaction.__exit__(*sys.exc_info())
            raise

    def throw(self, *args, **kwargs):
        txn = self.transaction

        # transaction may not be active
        if not txn._settings:
            return super(NRViewCoroutineWrapper, self).throw(*args, **kwargs)

        txn.save_transaction()
        try:
            return super(NRViewCoroutineWrapper, self).throw(*args, **kwargs)
        except:
            self.transaction.__exit__(*sys.exc_info())
            raise

    def close(self):
        txn = self.transaction

        # transaction may not be active
        if not txn._settings:
            return super(NRViewCoroutineWrapper, self).close()

        txn.save_transaction()
        try:
            r = super(NRViewCoroutineWrapper, self).close()
            self.transaction.__exit__(None, None, None)
            return r
        except:
            self.transaction.__exit__(*sys.exc_info())
            raise


@function_wrapper
def _nr_aiohttp_view_wrapper_(wrapped, instance, args, kwargs):
    # get the coroutine
    coro = wrapped(*args, **kwargs)

    if hasattr(coro, '__iter__'):
        coro = iter(coro)

    name = instance and callable_name(instance) or callable_name(wrapped)

    # Wrap the coroutine
    return NRViewCoroutineWrapper(name, coro, None)


def _nr_aiohttp_wrap_view_(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    instance._handler = _nr_aiohttp_view_wrapper_(instance._handler)
    return result


def instrument_aiohttp_web_urldispatcher(module):
    wrap_function_wrapper(module, 'ResourceRoute.__init__',
            _nr_aiohttp_wrap_view_)
