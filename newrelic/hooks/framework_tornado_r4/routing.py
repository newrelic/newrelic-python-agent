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

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction_context import TransactionContext
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import (wrap_function_wrapper, ObjectProxy,
        function_wrapper)

_logger = logging.getLogger(__name__)


def _iscoroutinefunction_tornado(fn):
    return hasattr(fn, '__tornado_coroutine__')


def _iscoroutinefunction_native(fn):
    return _asyncio_iscoroutinefunction(fn) or _inspect_iscoroutinefunction(fn)


def _nr_rulerouter_process_rule(wrapped, instance, args, kwargs):
    def _bind_params(rule, *args, **kwargs):
        return rule

    rule = _bind_params(*args, **kwargs)

    _wrap_handlers(rule)

    return wrapped(*args, **kwargs)


def _wrap_handlers(rule):
    if isinstance(rule, (tuple, list)):
        handler = rule[1]
    else:
        handler = rule.target

    if isinstance(handler, (tuple, list)):
        # Tornado supports nested rules. For example
        #
        # application = web.Application([
        #     (HostMatches("example.com"), [
        #         (r"/", MainPageHandler),
        #         (r"/feed", FeedHandler),
        #     ]),
        # ])
        for subrule in handler:
            _wrap_handlers(subrule)
        return

    elif not hasattr(handler, '_execute'):
        # This handler probably does not inherit from RequestHandler so we
        # ignore it. Tornado supports non class based views and this is
        # probably one of those.
        return

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


@function_wrapper
def _nr_request_end(wrapped, instance, args, kwargs):
    if hasattr(instance, '_nr_transaction'):
        transaction = instance._nr_transaction
        with TransactionContext(transaction):
            transaction.__exit__(None, None, None)

    # Execute the wrapped on_finish after ending the transaction since the
    # response has now already been sent.
    return wrapped(*args, **kwargs)


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


def instrument_tornado_routing(module):
    wrap_function_wrapper(module, 'RuleRouter.process_rule',
            _nr_rulerouter_process_rule)
