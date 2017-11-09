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
from newrelic.core.agent import remove_thread_utilization

_logger = logging.getLogger(__name__)
_VERSION = None


def _iscoroutinefunction_tornado(fn):
    return hasattr(fn, '__tornado_coroutine__')


def _iscoroutinefunction_native(fn):
    return _asyncio_iscoroutinefunction(fn) or _inspect_iscoroutinefunction(fn)


def _store_version_info():
    import tornado
    global _VERSION

    try:
        _VERSION = '.'.join(map(str, tornado.version_info))
    except:
        pass


def _nr_request_handler_init(wrapped, instance, args, kwargs):
    if current_transaction() is not None:
        _logger.error('Attempting to make a request (new transaction) when a '
                'transaction is already running. Please report this issue to '
                'New Relic support.\n%s',
                ''.join(traceback.format_stack()[:-1]))
        return wrapped(*args, **kwargs)

    app = application_instance()
    txn = WebTransaction(app, {})
    txn.__enter__()

    if txn.enabled:
        txn.drop_transaction()
        instance._nr_transaction = txn

    name = callable_name(instance)
    txn.set_transaction_name(name)

    # Record framework information for generation of framework metrics.
    txn.add_framework_info('Tornado/ASYNC', _VERSION)

    return wrapped(*args, **kwargs)


def _nr_application_init(wrapped, instance, args, kwargs):
    def _bind_params(handlers, *args, **kwargs):
        return handlers or []

    handlers = _bind_params(*args, **kwargs)

    for _, handler in handlers:
        if not hasattr(handler, '_execute'):
            # This handler probably does not inherit from RequestHandler so we
            # ignore it. Tornado supports non class based views and this is
            # probably one of those.
            continue

        # There are two cases we are protecting for by using this check. First
        # is handlers that subclass from other user defined handlers. In that
        # case, we want to be sure to wrap the original methods and not those
        # from the parent class. Second is the case where more than one
        # Application object is created in which case we again need to be sure
        # we are wrapping the original method.
        wrap_complete = hasattr(handler, '_nr_wrap_complete')

        # Wrap on_finish which will end transactions
        on_finish = handler.on_finish
        if wrap_complete:
            on_finish = getattr(on_finish, '__wrapped__', on_finish)
        setattr(handler, 'on_finish', _nr_request_end(on_finish))

        # Wrap all supported view methods with our FunctionTrace
        # instrumentation
        for request_method in handler.SUPPORTED_METHODS:
            method = getattr(handler, request_method.lower(), None)
            if not method:
                continue

            if wrap_complete:
                method = getattr(method, '__wrapped__', method)

            name = callable_name(method)
            wrapped_method = _nr_method(name)(method)
            setattr(handler, request_method.lower(), wrapped_method)

        handler._nr_wrap_complete = True

    return wrapped(*args, **kwargs)


@function_wrapper
def _nr_request_end(wrapped, instance, args, kwargs):
    if hasattr(instance, '_nr_transaction'):
        transaction = instance._nr_transaction
        with TransactionContext(transaction):
            transaction.__exit__(None, None, None)

    # Execute the wrapped on_finish after ending the transaction since the
    # response has now already been sent.
    return wrapped(*args, **kwargs)


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

        transaction.set_transaction_name(name)

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

    # Thread utilization data is meaningless in a tornado app. Remove it here,
    # once, since we know that tornado has been imported now. The following
    # call to agent_instance will initialize data sources, if they have not
    # been already. Thus, we know that this is a single place that we can
    # remove the thread utilization, regardless of the order of imports/agent
    # registration.

    remove_thread_utilization()

    wrap_function_wrapper(module, 'Application.__init__',
            _nr_application_init)
    wrap_function_wrapper(module, 'RequestHandler.__init__',
            _nr_request_handler_init)
    wrap_function_wrapper(module, 'RequestHandler.on_finish',
            _nr_request_end)

    _store_version_info()
