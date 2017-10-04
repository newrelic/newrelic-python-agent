import asyncio
import sys

from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import (wrap_function_wrapper,
        function_wrapper, ObjectProxy)
from newrelic.common.object_names import callable_name


class NRTransactionCoroutineWrapper(ObjectProxy):
    def __init__(self, wrapped, request):
        super(NRTransactionCoroutineWrapper, self).__init__(wrapped)
        self._nr_transaction = None

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

            import aiohttp
            txn.add_framework_info(
                    name='aiohttp', version=aiohttp.__version__)

            self._nr_transaction = txn

            if txn._settings:
                txn.__enter__()
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
        except (GeneratorExit, StopIteration):
            self._nr_transaction.__exit__(None, None, None)
            raise
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
        except (GeneratorExit, StopIteration):
            self._nr_transaction.__exit__(None, None, None)
            raise
        except:
            self._nr_transaction.__exit__(*sys.exc_info())
            raise


@function_wrapper
def _nr_aiohttp_view_wrapper_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    # get the coroutine
    coro = wrapped(*args, **kwargs)

    if hasattr(coro, '__iter__'):
        coro = iter(coro)

    name = instance and callable_name(instance) or callable_name(wrapped)
    transaction.set_transaction_name(name, priority=1)

    @asyncio.coroutine
    def _inner():
        with FunctionTrace(transaction, name):
            result = yield from coro

        return result

    return _inner()


def _nr_aiohttp_transaction_wrapper_(wrapped, instance, args, kwargs):

    def _bind_params(request, *_args, **_kwargs):
        return request

    # get the coroutine
    coro = wrapped(*args, **kwargs)
    request = _bind_params(*args, **kwargs)

    if hasattr(coro, '__iter__'):
        coro = iter(coro)

    # Wrap the coroutine
    return NRTransactionCoroutineWrapper(coro, request)


def _nr_aiohttp_wrap_view_(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    instance._handler = _nr_aiohttp_view_wrapper_(instance._handler)
    return result


def _nr_aiohttp_wrap_wsgi_response_(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    # We need to defer grabbing the response attribute in the case that the
    # WSGI application chooses not to call start_response before the first
    # iteration. The case where WSGI applications choose not to call
    # start_response before iteration is documented in the WSGI spec
    # (PEP-3333).
    #
    # > ...servers must not assume that start_response() has been called before
    # they begin iterating over the iterable.
    class ResponseProxy:
        def __getattr__(self, name):
            # instance.response should be overwritten at this point
            if instance.response is self:
                raise AttributeError("%r object has no attribute %r" % (
                        type(instance).__name__, 'response'))
            return getattr(instance.response, name)

    instance.response = ResponseProxy()

    return result


def instrument_aiohttp_web_urldispatcher(module):
    wrap_function_wrapper(module, 'ResourceRoute.__init__',
            _nr_aiohttp_wrap_view_)


def instrument_aiohttp_web(module):
    wrap_function_wrapper(module, 'Application._handle',
            _nr_aiohttp_transaction_wrapper_)


def instrument_aiohttp_wsgi(module):
    wrap_function_wrapper(module, 'WsgiResponse.__init__',
            _nr_aiohttp_wrap_wsgi_response_)
