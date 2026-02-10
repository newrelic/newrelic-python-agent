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


class GeneratorProxy(ObjectProxy):
    def __init__(self, wrapped, on_stop_iteration, on_error):
        super().__init__(wrapped)
        self._nr_on_stop_iteration = on_stop_iteration
        self._nr_on_error = on_error

    def __iter__(self):
        self._nr_wrapped_iter = self.__wrapped__.__iter__()
        return self

    def __next__(self):
        transaction = current_transaction()
        if not transaction:
            return self._nr_wrapped_iter.__next__()

        return_val = None
        try:
            return_val = self._nr_wrapped_iter.__next__()
        except StopIteration:
            self._nr_on_stop_iteration(self, transaction)
            raise
        except Exception:
            self._nr_on_error(self, transaction)
            raise
        return return_val

    def close(self):
        return self.__wrapped__.close()

    def __copy__(self):
        # Required to properly interface with itertool.tee, which can be called by LangChain on generators
        self.__wrapped__, copy = itertools.tee(self.__wrapped__, 2)
        return GeneratorProxy(copy, self._nr_on_stop_iteration, self._nr_on_error)


class AsyncGeneratorProxy(ObjectProxy):
    def __init__(self, wrapped, on_stop_iteration, on_error):
        super().__init__(wrapped)
        self._nr_on_stop_iteration = on_stop_iteration
        self._nr_on_error = on_error

    def __aiter__(self):
        self._nr_wrapped_iter = self.__wrapped__.__aiter__()
        return self

    async def __anext__(self):
        transaction = current_transaction()
        if not transaction:
            return await self._nr_wrapped_iter.__anext__()

        return_val = None
        try:
            return_val = await self._nr_wrapped_iter.__anext__()
        except StopAsyncIteration:
            self._nr_on_stop_iteration(self, transaction)
            raise
        except Exception:
            self._nr_on_error(self, transaction)
            raise
        return return_val

    async def aclose(self):
        return await self.__wrapped__.aclose()

    def __copy__(self):
        # Required to properly interface with itertool.tee, which can be called by LangChain on generators
        self.__wrapped__, copy = itertools.tee(self.__wrapped__, n=2)
        return AsyncGeneratorProxy(copy, self._nr_on_stop_iteration, self._nr_on_error)
