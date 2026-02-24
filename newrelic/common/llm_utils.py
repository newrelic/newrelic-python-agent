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

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy

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


class LLMStreamProxy(ObjectProxy):
    def __init__(self, wrapped, on_stop_iteration, on_error):
        super().__init__(wrapped)
        self._nr_on_stop_iteration = on_stop_iteration
        self._nr_on_error = on_error
        # Track if we've sent the LLM events yet to avoid sending them multiple times
        self._nr_closed = False

    def __iter__(self):
        self._nr_wrapped_iter = self.__wrapped__.__iter__()
        return self

    def __next__(self):
        return_val = None
        try:
            return_val = self._nr_wrapped_iter.__next__()
        except StopIteration:
            self._nr_closed = True
            transaction = current_transaction()
            if transaction:
                self._nr_on_stop_iteration(self, transaction)
            raise
        except Exception:
            self._nr_closed = True
            transaction = current_transaction()
            if transaction:
                self._nr_on_error(self, transaction)
            raise
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
        return LLMStreamProxy(copy, self._nr_on_stop_iteration, self._nr_on_error)


class AsyncLLMStreamProxy(ObjectProxy):
    def __init__(self, wrapped, on_stop_iteration, on_error):
        super().__init__(wrapped)
        self._nr_on_stop_iteration = on_stop_iteration
        self._nr_on_error = on_error
        # Track if we've sent the LLM events yet to avoid sending them multiple times
        self._nr_closed = False

    def __aiter__(self):
        self._nr_wrapped_iter = self.__wrapped__.__aiter__()
        return self

    async def __anext__(self):
        return_val = None
        try:
            return_val = await self._nr_wrapped_iter.__anext__()
        except StopAsyncIteration:
            self._nr_closed = True
            transaction = current_transaction()
            if transaction:
                self._nr_on_stop_iteration(self, transaction)
            raise
        except Exception:
            self._nr_closed = True
            transaction = current_transaction()
            if transaction:
                self._nr_on_error(self, transaction)
            raise
        return return_val

    async def aclose(self):
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
        if self._nr_closed:
            # If we already sent the related events, we can just call athrow as there's nothing left to do.
            return await self.__wrapped__.athrow(*args)

        transaction = current_transaction()
        if transaction:
            # Send the events as if we were hitting an exception.
            self._nr_closed = True
            self._nr_on_error(self, transaction)

        return await self.__wrapped__.athrow(*args)

    def __copy__(self):
        # Required to properly interface with itertool.tee, which can be called by LangChain on generators
        self.__wrapped__, copy = itertools.tee(self.__wrapped__, n=2)
        return AsyncLLMStreamProxy(copy, self._nr_on_stop_iteration, self._nr_on_error)
