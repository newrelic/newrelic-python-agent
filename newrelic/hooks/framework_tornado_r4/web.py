import inspect
try:
    _inspect_iscoroutinefunction = inspect.iscoroutinefunction
except AttributeError:
    def _inspect_iscoroutinefunction(*args, **kwargs):
        return False

try:
    import asyncio
    _asyncio_iscoroutinefunction = asyncio.iscoroutinefunction
except ImportError:
    def _asyncio_iscoroutinefunction(*args, **kwargs):
        return False

import logging
import traceback

from newrelic.api.application import application_instance
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction
from newrelic.api.transaction_context import TransactionContext
from newrelic.api.web_transaction import WebTransaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import (wrap_function_wrapper, ObjectProxy,
        function_wrapper)

_logger = logging.getLogger(__name__)


def _iscoroutinefunction_tornado(fn):
    return hasattr(fn, '__tornado_coroutine__')


def _iscoroutinefunction_native(fn):
    return _asyncio_iscoroutinefunction(fn) or _inspect_iscoroutinefunction(fn)


def _nr_request_handler_init(wrapped, instance, args, kwargs):
    if current_transaction() is not None:
        _logger.error('Attempting to make a request (new transaction) when a '
                'transaction is already running. Please report this issue to '
                'New Relic support.\n%s',
                ''.join(traceback.format_stack()[:-1]))
        return wrapped(*args, **kwargs)

    app = application_instance()

    def _bind_params(application, request, *args, **kwargs):
        return request

    request = _bind_params(*args, **kwargs)

    txn = WebTransaction(app, {})
    txn.__enter__()

    if txn.enabled:
        txn.drop_transaction()
        instance._nr_transaction = txn

    if request.method not in instance.SUPPORTED_METHODS:
        # If the method isn't one of the supported ones, then we expect the
        # wrapped method to raise an exception for HTTPError(405). In this case
        # we name the transaction after the wrapped method.
        name = callable_name(instance)
    else:
        # Otherwise we name the transaction after the handler function that
        # should end up being executed for the request.
        method = getattr(instance, request.method.lower())
        name = callable_name(method)

        # Wrap the method with our FunctionTrace instrumentation
        setattr(instance, request.method.lower(), _nr_method(name)(method))

    txn.set_transaction_name(name)

    return wrapped(*args, **kwargs)


def _nr_request_end(wrapped, instance, args, kwargs):
    transaction = getattr(instance, '_nr_transaction', None)
    if transaction is None:
        return wrapped(*args, **kwargs)

    with TransactionContext(transaction):
        try:
            ret = wrapped(*args, **kwargs)
        except Exception:
            raise
        finally:
            transaction.__exit__(None, None, None)

    return ret


class NRFunctionTraceCoroutineWrapper(ObjectProxy):
    def __init__(self, wrapped, transaction, name):
        super(NRFunctionTraceCoroutineWrapper, self).__init__(wrapped)
        self._nr_transaction = transaction
        self._nr_trace = FunctionTrace(transaction, name)

    def __iter__(self):
        return self

    def __await__(self):
        return self

    def __next__(self):
        return self.send(None)

    next = __next__

    def send(self, value):
        if not self._nr_trace.activated:
            self._nr_trace.__enter__()

        with TransactionContext(self._nr_transaction):
            try:
                return self.__wrapped__.send(value)
            except:
                self._nr_trace.__exit__(None, None, None)
                raise

    def throw(self, *args, **kwargs):
        with TransactionContext(self._nr_transaction):
            try:
                return self.__wrapped__.throw(*args, **kwargs)
            except:
                self._nr_trace.__exit__(None, None, None)
                raise

    def close(self):
        try:
            return self.__wrapped__.close()
        finally:
            self._nr_trace.__exit__(None, None, None)


def _nr_method(name):

    @function_wrapper
    def wrapper(wrapped, instance, args, kwargs):
        transaction = getattr(instance, '_nr_transaction', None)

        if transaction is None:
            return wrapped(*args, **kwargs)

        if (_iscoroutinefunction_tornado(wrapped) and
                inspect.isgeneratorfunction(wrapped.__wrapped__)):
            method = wrapped.__wrapped__

            import tornado.gen

            @tornado.gen.coroutine
            def _wrapped_coro():
                coro = method(instance, *args, **kwargs)
                return NRFunctionTraceCoroutineWrapper(coro, transaction, name)

            return _wrapped_coro()
        elif _iscoroutinefunction_native(wrapped):
            coro = wrapped(*args, **kwargs)
            return NRFunctionTraceCoroutineWrapper(coro, transaction, name)
        else:
            with TransactionContext(transaction):
                with FunctionTrace(transaction, name):
                    return wrapped(*args, **kwargs)

    return wrapper


def instrument_tornado_web(module):
    wrap_function_wrapper(module, 'RequestHandler.__init__',
            _nr_request_handler_init)
    wrap_function_wrapper(module, 'RequestHandler.on_finish',
            _nr_request_end)
