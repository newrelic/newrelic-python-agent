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

import inspect
import logging

from newrelic.api.transaction import current_transaction

_logger = logging.getLogger(__name__)


class WithLlmCustomAttributes(object):
    nesting_level = 0
    attr_dict = {}

    def __init__(self, custom_attr_dict):
        transaction = current_transaction()
        if not custom_attr_dict or not isinstance(custom_attr_dict, dict):
            raise TypeError(
                "custom_attr_dict must be a non-empty dictionary. Received type: %s" % type(custom_attr_dict)
            )

        # Add "llm." prefix to all keys in attribute dictionary
        context_attrs = {k if k.startswith("llm.") else f"llm.{k}": v for k, v in custom_attr_dict.items()}

        # Support merging contexts in nested cases
        WithLlmCustomAttributes.attr_dict.update(context_attrs)

        self.transaction = transaction

    def __enter__(self):
        WithLlmCustomAttributes.nesting_level += 1

        if not self.transaction:
            _logger.warning("WithLlmCustomAttributes must be called within the scope of a transaction.")
            return self

        self.transaction._llm_context_attrs = self.attr_dict
        return self

    def __exit__(self, exc, value, tb):
        WithLlmCustomAttributes.nesting_level -= 1

        # Clear out context attributes once we leave the current context
        # Check whether we are in a nested context manager case and only clear the contexts attrs if not
        if self.transaction and WithLlmCustomAttributes.nesting_level == 0:
            del self.transaction._llm_context_attrs
