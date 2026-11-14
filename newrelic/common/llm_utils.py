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

import itertools
import logging
import weakref

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy
from newrelic.core.trace_cache import current_task, trace_cache

_logger = logging.getLogger(__name__)


def _get_llm_metadata(transaction):
    if not transaction:
        return {}
    try:
        # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
        custom_attrs_dict = getattr(transaction, "_custom_params", {})
        llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}
        llm_context_attrs = getattr(transaction, "_llm_context_attrs", None)
        if llm_context_attrs:
            llm_metadata_dict.update(llm_context_attrs)
    except Exception:
        _logger.warning("Unable to capture custom metadata attributes to record on LLM events.")
        return {}

    return llm_metadata_dict


def noop(self, *args, **kwargs):
    """No-op function to use as a default for on_stream_chunk when it's not provided."""
    pass


class LLMStreamProxy(ObjectProxy):
    def __init__(self, wrapped, on_stop_iteration, on_error, on_stream_chunk=None):
        super().__init__(wrapped)
        self._nr_on_stop_iteration = on_stop_iteration
        self._nr_on_error = on_error
        self._nr_on_stream_chunk = on_stream_chunk or noop
        # Track if we've sent the LLM events yet to avoid sending them multiple times
        self._nr_closed = False

    def __iter__(self):
        self._nr_wrapped_iter = self.__wrapped__.__iter__()
        return self

    def __next__(self):
        try:
            return_val = self._nr_wrapped_iter.__next__()
            self._nr_on_stream_chunk(self, return_val)
        except StopIteration:
            transaction = current_transaction()
            if transaction:
                self._nr_closed = True
                self._nr_on_stop_iteration(self, transaction)
            raise
        except Exception:
            transaction = current_transaction()
            if transaction:
                self._nr_closed = True
                self._nr_on_error(self, transaction)
            raise
        else:
            return return_val

    def close(self):
        if self._nr_closed:
            # If we already sent the related events, we can just call close as there's nothing left to do.
            return self.__wrapped__.close()

        transaction = current_transaction()
        if transaction:
            # Send the events as if we were hitting StopIteration.
            self._nr_closed = True
            self._nr_on_stop_iteration(self, transaction)

        return self.__wrapped__.close()

    def throw(self, *args):
        if self._nr_closed:
            # If we already sent the related events, we can just call throw as there's nothing left to do.
            return self.__wrapped__.throw(*args)

        transaction = current_transaction()
        if transaction:
            # Send the events as if we were hitting an exception.
            self._nr_closed = True
            self._nr_on_error(self, transaction)

        return self.__wrapped__.throw(*args)

    def __copy__(self):
        # Required to properly interface with itertool.tee, which can be called by LangChain on generators
        self.__wrapped__, copy = itertools.tee(self.__wrapped__, 2)
        return LLMStreamProxy(
            copy,
            on_stop_iteration=self._nr_on_stop_iteration,
            on_error=self._nr_on_error,
            on_stream_chunk=self._nr_on_stream_chunk,
        )


class AsyncLLMStreamProxy(ObjectProxy):
    def __init__(self, wrapped, on_stop_iteration, on_error, on_stream_chunk=None):
        super().__init__(wrapped)
        self._nr_on_stop_iteration = on_stop_iteration
        self._nr_on_error = on_error
        self._nr_on_stream_chunk = on_stream_chunk or noop
        # Track if we've sent the LLM events yet to avoid sending them multiple times
        self._nr_closed = False
        # Lazily established by __aiter__ or __anext__.
        self._nr_wrapped_iter = None
        # A stream that is abandoned (a break or a raise in the body of an async for) is never exhausted or
        # closed, so its trace stays open and is dropped along with its parent. If the task that created the
        # stream, and so opened its trace, also iterates it, finish it as if it were closed when that task
        # finishes. Streams consumed from another task are left as they are. The transaction is held weakly so
        # a proxy kept around by the application doesn't keep a recorded transaction alive.
        transaction = current_transaction()
        self._nr_transaction = weakref.ref(transaction) if transaction else None
        self._nr_creator_task = current_task(trace_cache().asyncio)
        self._nr_watched_task = None

    def __aiter__(self):
        self._nr_wrapped_iter = self.__wrapped__.__aiter__()
        return self

    async def __anext__(self):
        # If wrapped iter is not established by this point, establish it to allow lazy iteration.
        if self._nr_wrapped_iter is None:
            self._nr_wrapped_iter = self.__wrapped__.__aiter__()

        if self._nr_creator_task is not None:
            self._nr_watch_task()

        try:
            return_val = await self._nr_wrapped_iter.__anext__()
            self._nr_on_stream_chunk(self, return_val)
        except StopAsyncIteration:
            self._nr_unwatch_task()
            transaction = current_transaction()
            if transaction:
                self._nr_closed = True
                self._nr_on_stop_iteration(self, transaction)
            raise
        except Exception:
            self._nr_unwatch_task()
            transaction = current_transaction()
            if transaction:
                self._nr_closed = True
                self._nr_on_error(self, transaction)
            raise
        else:
            return return_val

    async def aclose(self):
        self._nr_unwatch_task()
        if self._nr_closed:
            # If we already sent the related events, we can just call aclose as there's nothing left to do.
            return await self.__wrapped__.aclose()

        transaction = current_transaction()
        if transaction:
            # Send the events as if we were hitting StopAsyncIteration.
            self._nr_closed = True
            self._nr_on_stop_iteration(self, transaction)

        return await self.__wrapped__.aclose()

    async def athrow(self, *args):
        self._nr_unwatch_task()
        if self._nr_closed:
            # If we already sent the related events, we can just call athrow as there's nothing left to do.
            return await self.__wrapped__.athrow(*args)

        transaction = current_transaction()
        if transaction:
            # Send the events as if we were hitting an exception.
            self._nr_closed = True
            self._nr_on_error(self, transaction)

        return await self.__wrapped__.athrow(*args)

    def _nr_watch_task(self):
        # Runs on the first iteration only.
        creator_task, self._nr_creator_task = self._nr_creator_task, None
        transaction = self._nr_transaction and self._nr_transaction()
        if not transaction or creator_task is not current_task(trace_cache().asyncio):
            return
        # A transaction started in this task is recorded before the task finishes, so the callback could never
        # report anything; registering would only keep this stream alive for the life of the task.
        if getattr(transaction.root_span, "_task", None) is creator_task:
            return

        trace_cache().add_task_stop_callback(creator_task, self._nr_on_task_done)
        self._nr_watched_task = creator_task

    def _nr_unwatch_task(self):
        task, self._nr_watched_task = self._nr_watched_task, None
        if task is not None:
            trace_cache().remove_task_stop_callback(task, self._nr_on_task_done)

    def _nr_on_task_done(self, task):
        self._nr_watched_task = None
        transaction = self._nr_transaction and self._nr_transaction()
        if self._nr_closed or not transaction or transaction.state != transaction.STATE_RUNNING:
            return

        self._nr_closed = True
        try:
            # Send the events as if the stream had been closed, matching aclose().
            self._nr_on_stop_iteration(self, transaction)
        except Exception:
            _logger.warning("Unable to record events for an LLM stream abandoned by its task.", exc_info=True)

    def __copy__(self):
        # Required to properly interface with itertool.tee, which can be called by LangChain on generators
        self.__wrapped__, copy = itertools.tee(self.__wrapped__, n=2)
        return AsyncLLMStreamProxy(
            copy,
            on_stop_iteration=self._nr_on_stop_iteration,
            on_error=self._nr_on_error,
            on_stream_chunk=self._nr_on_stream_chunk,
        )
