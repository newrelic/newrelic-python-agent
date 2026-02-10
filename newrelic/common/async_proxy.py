# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import time

from newrelic.common.coroutine import (
    is_async_generator_function,
    is_asyncio_coroutine,
    is_coroutine_callable,
    is_generator_function,
)
from newrelic.common.object_wrapper import ObjectProxy
from newrelic.core.trace_cache import trace_cache

_logger = logging.getLogger(__name__)

CancelledError = None


class TransactionContext:
    def __init__(self, transaction_init):
        self.enter_time = None
        self.transaction = None
        self.transaction_init = transaction_init
        # This flag is used to tell if the top level coroutine is an async generator.
        # Depending on the conditions, the behavior when encountering
        # StopIteration vs StopAsyncIteration is different. See the comments in __exit__
        # for details on the expected behavior.
        self.is_async_generator = False

    def pre_close(self):
        # If close is called prior to the start of the coroutine do not create
        # a transaction.
        self.transaction_init = None

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
        # If no transaction attempt to create it if first time entering context
        # manager.
        if self.transaction_init:
            current_trace = trace_cache().prepare_for_root()
            current_transaction = current_trace and current_trace.transaction

            # If the current transaction's Sentinel is exited we can ignore it.
            if not current_transaction:
                self.transaction = self.transaction_init(None)
            else:
                self.transaction = self.transaction_init(current_transaction)

            # Set transaction_init to None so we only attempt to create a
            # transaction the first time entering the context.
            self.transaction_init = None
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
                from asyncio import CancelledError
            except:
                CancelledError = GeneratorExit

        # There are 3 separate cases we need to consider for when attempting to exit this context manager.
        #
        # When running as a generator, the execution path is simple. When StopIteration or GeneratorExit
        # is raised, the generator has completed normally so we complete the transaction. Other exceptions
        # are treated as errors and the transaction is closed with the exception details.
        #
        # When running as a coroutine, the execution path is only slightly changed. Calling __await__ on
        # the coroutine will return a generator which is driven to completion. Since CoroutineProxy wraps
        # this generator in a GeneratorProxy, the execution path ends up as the same as a generator, with
        # the additional consideration of asyncio.CancelledError which is raised if the coroutine is cancelled.
        # This is treated the same as GeneratorExit, completing the transaction without error.
        #
        # When running as an async generator, the execution path is considerably more complex. All of the
        # interfaces for the async generator (__anext__, asend, athrow, aclose) are coroutines which themselves
        # require context management. These coroutines are awaited, which again creates a generator that must also
        # be tracked. This means that the TransactionContext will be entered and exited multiple times with
        # StopIteration being thrown in an underlying generator for each item that's yielded from the async generator.
        # We therefore need to avoid completing the transaction when StopIteration is raised, and only complete
        # the transaction when StopAsyncIteration is raised which indicates the async generator has completed normally.
        # GeneratorExit and asyncio.CancelledError are treated the same as the other cases, completing the transaction
        # without error.
        #
        # The is_async_generator flag is used to tell if the top level coroutine is an async generator, which will
        # then change the behavior with respect to StopIteration. As this TransactionContext object is shared
        # between all the wrappers for async generators, the coroutines they create, and the generators created
        # by awaiting those coroutines, we have to change the behavior of all of these types of wrappers when
        # run under an async generator to avoid completing the transaction early.

        if exc is StopAsyncIteration:
            # If an async generator completes normally, complete the transaction without error.
            # This condition is also manually run when an async generator is closed via AsyncGeneratorProxy.aclose().
            if self.is_async_generator:
                self.transaction.__exit__(None, None, None)
            # If a non-async generator reaches this, complete the transaction and report as an error.
            else:
                self.transaction.__exit__(exc, value, tb)

        elif exc is StopIteration:
            # If a non-async generator completes normally, complete the transaction without error.
            if not self.is_async_generator:
                self.transaction.__exit__(None, None, None)

            # If an async generator reaches this, don't complete the transaction as this is
            # caused by yielding an item from the generator. This is due to completing the
            # underlying coroutine which is a generator internally and will raise StopIteration.
            # We need to wait until the async generator itself completes normally with
            # a final StopAsyncIteration.

            # Note: This block is equivalent to "else: pass".
            # If this code block is unnested in the future, that should be made explicit.

        # If coroutine was cancelled, either by asyncio.CancelledError, .close(),
        # complete the transaction without error.
        elif exc in (GeneratorExit, CancelledError):
            self.transaction.__exit__(None, None, None)

        # Unexpected exception, complete the transaction and report as an error.
        elif exc:
            self.transaction.__exit__(exc, value, tb)


class LoopContext:
    def __enter__(self):
        self.enter_time = time.time()

    def __exit__(self, exc, value, tb):
        trace_cache().record_event_loop_wait(self.enter_time, time.time())


class Coroutine(ObjectProxy):
    def __init__(self, wrapped, context):
        super().__init__(wrapped)
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

    def __next__(self):
        return self.send(None)


class AwaitableGeneratorProxy(GeneratorProxy):
    def __await__(self):
        return self


class CoroutineProxy(Coroutine):
    def __await__(self):
        return GeneratorProxy(self.__wrapped__, self._nr_context)


class AsyncGeneratorProxy(ObjectProxy):
    def __init__(self, wrapped, context):
        super().__init__(wrapped)
        self._nr_context = context
        # Set this flag to indicate that the top level coroutine is an async generator,
        # which will change the behavior of __exit__ in TransactionContext for all the
        # lower level wrappers.
        self._nr_context.is_async_generator = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.asend(None)

    async def asend(self, value):
        return await CoroutineProxy(self.__wrapped__.asend(value), self._nr_context)

    async def athrow(self, *args, **kwargs):
        return await CoroutineProxy(self.__wrapped__.athrow(*args, **kwargs), self._nr_context)

    async def aclose(self):
        try:
            return await CoroutineProxy(self.__wrapped__.aclose(), self._nr_context)
        finally:
            # There is nothing further down that can tell correctly that the async generator
            # is being closed, so we call __exit__ with StopAsyncIteration manually to ensure
            # the transaction is correctly completed without error. Otherwise this would rely on
            # the garbage collector deleting the async generator to complete the transaction by
            # calling Transaction.__del__, which will cause a hanging transaction and race conditions.
            self._nr_context.__exit__(StopAsyncIteration, None, None)


def async_proxy(wrapped):
    if is_coroutine_callable(wrapped):
        return CoroutineProxy
    elif is_async_generator_function(wrapped):
        return AsyncGeneratorProxy
    elif is_generator_function(wrapped):
        if is_asyncio_coroutine(wrapped):
            return AwaitableGeneratorProxy
        else:
            return GeneratorProxy
