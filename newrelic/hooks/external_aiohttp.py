import sys

from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace
from newrelic.common.object_wrapper import wrap_function_wrapper
from asyncio.coroutines import CoroWrapper


class NRRequestCoroutineWrapper(CoroWrapper):
    def __init__(self, url, method, gen, func=None):
        super(NRRequestCoroutineWrapper, self).__init__(gen, func)
        txn = current_transaction()
        self.trace = ExternalTrace(txn,
                'aiohttp_client', url, method)

    def __next__(self):
        if not self.trace.transaction:
            return self.gen.send(None)

        if not self.trace.activated:
            self.trace.__enter__()
            if self.trace.transaction.current_node is self.trace:
                # externals should not have children
                self.trace.transaction._pop_current(self.trace)

        try:
            return self.gen.send(None)
        except StopIteration:
            self.trace.__exit__(None, None, None)
            raise
        except:
            self.trace.__exit__(*sys.exc_info())
            raise

    def throw(self, *args, **kwargs):
        try:
            r = super(NRRequestCoroutineWrapper, self).throw(*args, **kwargs)
            self.trace.__exit__(None, None, None)
            return r
        except:
            self.trace.__exit__(*sys.exc_info())
            raise

    def close(self):
        try:
            r = super(NRRequestCoroutineWrapper, self).close()
            self.trace.__exit__(None, None, None)
            return r
        except:
            self.trace.__exit__(*sys.exc_info())
            raise


def _bind_request(method, url, *args, **kwargs):
    return method, url


def _nr_aiohttp_request_wrapper_(wrapped, instance, args, kwargs):
    coro = wrapped(*args, **kwargs)
    method, url = _bind_request(*args, **kwargs)
    return NRRequestCoroutineWrapper(url, method, coro, None)


def instrument_client(module):
    wrap_function_wrapper(module, 'ClientSession._request',
            _nr_aiohttp_request_wrapper_)
