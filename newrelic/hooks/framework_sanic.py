import asyncio
import sys

from newrelic.api.application import application_instance
from newrelic.api.web_transaction import WebTransaction
from newrelic.common.object_wrapper import wrap_function_wrapper, ObjectProxy


class NRTransactionCoroutineWrapper(ObjectProxy):
    def __init__(self, wrapped, request):
        super(NRTransactionCoroutineWrapper, self).__init__(wrapped)
        self._nr_transaction = None
        self._nr_request = request

        environ = {
            'PATH_INFO': request.path,
            'REQUEST_METHOD': request.method,
            'CONTENT_TYPE': request.content_type,
            'QUERY_STRING': request.query_string,
        }
        for k, v in request.headers.items():
            normalized_key = k.replace('-', '_').upper()
            http_key = 'HTTP_%s' % normalized_key
            environ[http_key] = v
        self._nr_environ = environ

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
            txn = WebTransaction(app, self._nr_environ)

            self._nr_transaction = txn

            if txn.enabled:
                txn.__enter__()
                txn.drop_transaction()

        txn = self._nr_transaction

        # transaction may not be active
        if not txn.enabled:
            return self.__wrapped__.send(value)

        txn.save_transaction()

        try:
            r = self.__wrapped__.send(value)
            txn.drop_transaction()
            return r
        except (GeneratorExit, StopIteration):
            self._nr_transaction.__exit__(None, None, None)
            self._nr_request = None
            raise
        except:
            self._nr_transaction.__exit__(*sys.exc_info())
            self._nr_request = None
            raise

    def throw(self, *args, **kwargs):
        txn = self._nr_transaction

        # transaction may not be active
        if not txn.enabled:
            return self.__wrapped__.throw(*args, **kwargs)

        txn.save_transaction()
        try:
            r = self.__wrapped__.throw(*args, **kwargs)
            txn.drop_transaction()
            return r
        except (GeneratorExit, StopIteration):
            self._nr_transaction.__exit__(None, None, None)
            self._nr_request = None
            raise
        except asyncio.CancelledError:
            self._nr_transaction.ignore_transaction = True
            self._nr_transaction.__exit__(None, None, None)
            self._nr_request = None
            raise
        except:
            self._nr_transaction.__exit__(*sys.exc_info())
            self._nr_request = None
            raise

    def close(self):
        txn = self._nr_transaction

        # transaction may not be active
        if not txn.enabled:
            return self.__wrapped__.close()

        txn.save_transaction()
        try:
            r = self.__wrapped__.close()
            self._nr_transaction.__exit__(None, None, None)
            self._nr_request = None
            return r
        except:
            self._nr_transaction.__exit__(*sys.exc_info())
            self._nr_request = None
            raise


def _bind_request(request, *args, **kwargs):
    return request


def _nr_sanic_transaction_wrapper_(wrapped, instance, args, kwargs):
    # get the coroutine
    coro = wrapped(*args, **kwargs)
    request = _bind_request(*args, **kwargs)

    if hasattr(coro, '__iter__'):
        coro = iter(coro)

    # Wrap the coroutine
    return NRTransactionCoroutineWrapper(coro, request)


def instrument_sanic_app(module):
    wrap_function_wrapper(module, 'Sanic.handle_request',
        _nr_sanic_transaction_wrapper_)
