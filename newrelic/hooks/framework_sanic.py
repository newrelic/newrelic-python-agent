import asyncio
import sys

from newrelic.api.application import application_instance
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import function_trace
from newrelic.common.object_wrapper import (wrap_function_wrapper, ObjectProxy,
    function_wrapper)
from newrelic.common.object_names import callable_name
from newrelic.core.config import ignore_status_code


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

            import sanic
            txn.add_framework_info(
                    name='Sanic', version=sanic.__version__)

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


def _bind_add(uri, methods, handler, *args, **kwargs):
    return uri, methods, handler, args, kwargs


@function_wrapper
def _nr_wrapper_handler_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = None
    if hasattr(wrapped, '_nr_handler_name'):
        name = wrapped._nr_handler_name

    if name is None:
        name = callable_name(wrapped)
        setattr(wrapped, '_nr_handler_name', name)

    transaction.set_transaction_name(name, priority=2)

    return function_trace(name=name)(wrapped)(*args, **kwargs)


def _nr_sanic_router_add(wrapped, instance, args, kwargs):
    uri, methods, handler, args, kwargs = _bind_add(*args, **kwargs)

    if not hasattr(handler, '_nr_handler_name'):
        name = callable_name(handler)
        setattr(handler, '_nr_handler_name', name)

    wrapped_handler = _nr_wrapper_handler_(handler)

    return wrapped(uri, methods, wrapped_handler, *args, **kwargs)


@function_wrapper
def _nr_wrapper_error_handler_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    name = None
    if hasattr(wrapped, '_nr_error_handler_name'):
        name = wrapped._nr_error_handler_name

    if name is None:
        name = callable_name(wrapped)
        setattr(wrapped, '_nr_error_handler_name', name)

    try:
        response = function_trace(name=name)(wrapped)(*args, **kwargs)
    except:
        transaction.record_exception()
        raise

    return response


def _bind_error_add(exception, handler, *args, **kwargs):
    return exception, handler


def _nr_sanic_error_handlers(wrapped, instance, args, kwargs):
    exception, handler = _bind_error_add(*args, **kwargs)

    if not hasattr(handler, '_nr_error_handler_name'):
        name = callable_name(handler)
        setattr(handler, '_nr_error_handler_name', name)

    wrapped_handler = _nr_wrapper_error_handler_(handler)

    return wrapped(exception, wrapped_handler)


@function_wrapper
def error_response(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    exc_info = sys.exc_info()
    try:
        response = wrapped(*args, **kwargs)
    except:
        transaction.record_exception(*exc_info)
        # We record the original exception and the exception generated by the
        # error handler
        transaction.record_exception()
        raise
    else:
        # response can be a response object or a coroutine
        if hasattr(response, 'status'):
            if not ignore_status_code(response.status):
                transaction.record_exception(*exc_info)
        else:
            transaction.record_exception(*exc_info)
    finally:
        exc_info = None

    return response


def _sanic_app_init(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    error_handler = getattr(instance, 'error_handler')
    if hasattr(error_handler, 'response'):
        instance.error_handler.response = error_response(
                error_handler.response)
    return result


def _nr_sanic_response_parse_headers(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    # instance is the response object
    cat_headers = transaction.process_response(str(instance.status),
            instance.headers.items())
    if cat_headers and ExternalTrace.cat_appdata_key not in instance.headers:
        instance.headers.update(cat_headers)

    return wrapped(*args, **kwargs)


@function_wrapper
def _nr_wrapper_middleware_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = None
    if hasattr(wrapped, '_nr_middleware_name'):
        name = wrapped._nr_middleware_name

    if name is None:
        name = callable_name(wrapped)
        setattr(wrapped, '_nr_middleware_name', name)

    return function_trace(name=name)(wrapped)(*args, **kwargs)


def _bind_middleware(middleware, *args, **kwargs):
    return middleware, args, kwargs


def _nr_sanic_register_middleware_(wrapped, instance, args, kwargs):
    middleware, args, kwargs = _bind_middleware(*args, **kwargs)

    if not hasattr(middleware, '_nr_middleware_name'):
        name = callable_name(middleware)
        setattr(middleware, '_nr_middleware_name', name)

    wrapped_middleware = _nr_wrapper_middleware_(middleware)
    wrapped(wrapped_middleware, *args, **kwargs)
    return middleware


def instrument_sanic_app(module):
    wrap_function_wrapper(module, 'Sanic.handle_request',
        _nr_sanic_transaction_wrapper_)
    wrap_function_wrapper(module, 'Sanic.__init__',
        _sanic_app_init)
    wrap_function_wrapper(module, 'Sanic.register_middleware',
        _nr_sanic_register_middleware_)


def instrument_sanic_router(module):
    wrap_function_wrapper(module, 'Router.add',
        _nr_sanic_router_add)


def instrument_sanic_response(module):
    wrap_function_wrapper(module, 'BaseHTTPResponse._parse_headers',
        _nr_sanic_response_parse_headers)


def instrument_sanic_handlers(module):
    wrap_function_wrapper(module, 'ErrorHandler.add',
        _nr_sanic_error_handlers)
