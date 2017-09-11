import sys

from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace
from newrelic.common.object_wrapper import wrap_function_wrapper, ObjectProxy


class NRRequestCoroutineWrapper(ObjectProxy):
    def __init__(self, url, method, wrapped, func=None):
        super(NRRequestCoroutineWrapper, self).__init__(wrapped)
        transaction = current_transaction()
        self._nr_trace = ExternalTrace(transaction,
                'aiohttp_client', url, method)

    def __iter__(self):
        return self

    def __await__(self):
        return self

    def __next__(self):
        if not self._nr_trace.transaction:
            return self.__wrapped__.send(None)

        if not self._nr_trace.activated:
            self._nr_trace.__enter__()
            if self._nr_trace.transaction.current_node is self._nr_trace:
                # externals should not have children
                self._nr_trace.transaction._pop_current(self._nr_trace)

        try:
            return self.__wrapped__.send(None)
        except StopIteration:
            self._nr_trace.__exit__(None, None, None)
            raise
        except:
            self._nr_trace.__exit__(*sys.exc_info())
            raise

    def throw(self, *args, **kwargs):
        try:
            r = self.__wrapped__.throw(*args, **kwargs)
            self._nr_trace.__exit__(None, None, None)
            return r
        except:
            self._nr_trace.__exit__(*sys.exc_info())
            raise

    def close(self):
        try:
            r = self.__wrapped__.close()
            self._nr_trace.__exit__(None, None, None)
            return r
        except:
            self._nr_trace.__exit__(*sys.exc_info())
            raise


def _bind_request(method, url, *args, **kwargs):
    return method, url


def _nr_aiohttp_request_wrapper_(wrapped, instance, args, kwargs):
    coro = wrapped(*args, **kwargs)
    method, url = _bind_request(*args, **kwargs)
    return NRRequestCoroutineWrapper(url, method, coro, None)


def instrument_aiohttp_client(module):
    wrap_function_wrapper(module, 'ClientSession._request',
            _nr_aiohttp_request_wrapper_)
