import logging
import time
import newrelic.packages.six as six

from newrelic.common.coroutine import (is_coroutine_function,
        is_asyncio_coroutine, is_generator_function)
from newrelic.common.object_wrapper import ObjectProxy
from newrelic.core.trace_cache import trace_cache

_logger = logging.getLogger(__name__)

CancelledError = None


class TransactionContext(object):
    def __init__(self, transaction):
        self.enter_time = None
        self.transaction = transaction
        if not self.transaction.enabled:
            self.transaction = None

    def pre_close(self):
        if self.transaction and not self.transaction._state:
            self.transaction = None

    def close(self):
        if not self.transaction:
            return

        if self.transaction._state:
            try:
                with self:
                    raise GeneratorExit
            except GeneratorExit:
                pass

    def __enter__(self):
        if not self.transaction:
            return self

        if not self.transaction._state:
            self.transaction.__enter__()

        self.enter_time = time.time()
        return self

    def __exit__(self, exc, value, tb):
        if not self.transaction:
            return

        if self.enter_time is not None:
            exit_time = time.time()
            start_time = self.enter_time
            self.enter_time = None

            trace_cache().record_event_loop_wait(start_time, exit_time)

        global CancelledError

        if CancelledError is None:
            try:
                from concurrent.futures import CancelledError
            except:
                CancelledError = GeneratorExit

        # case: coroutine completed or cancelled
        if (exc is StopIteration or exc is GeneratorExit or
                exc is CancelledError):
            self.transaction.__exit__(None, None, None)

        # case: coroutine completed because of error
        elif exc:
            self.transaction.__exit__(exc, value, tb)


class LoopContext(object):
    def __enter__(self):
        self.enter_time = time.time()

    def __exit__(self, exc, value, tb):
        trace_cache().record_event_loop_wait(self.enter_time, time.time())


class Coroutine(ObjectProxy):
    def __init__(self, wrapped, context):
        super(Coroutine, self).__init__(wrapped)
        self._nr_context = context

    def send(self, value):
        with self._nr_context:
            return self.__wrapped__.send(value)

    def throw(self, *args, **kwargs):
        with self._nr_context:
            return self.__wrapped__.throw(*args, **kwargs)

    def close(self):
        self._nr_context.pre_close()

        try:
            with self._nr_context:
                result = self.__wrapped__.close()
        except:
            raise

        self._nr_context.close()
        return result


class GeneratorProxy(Coroutine):
    def __iter__(self):
        return self

    if six.PY2:
        def next(self):
            return self.send(None)
    else:
        def __next__(self):
            return self.send(None)


class AwaitableGeneratorProxy(GeneratorProxy):
    def __await__(self):
        return self


class CoroutineProxy(Coroutine):
    def __await__(self):
        return GeneratorProxy(self.__wrapped__, self._nr_context)


def async_proxy(wrapped):
    if is_coroutine_function(wrapped):
        return CoroutineProxy
    elif is_generator_function(wrapped):
        if is_asyncio_coroutine(wrapped):
            return AwaitableGeneratorProxy
        else:
            return GeneratorProxy
