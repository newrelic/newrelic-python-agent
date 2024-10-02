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

import contextvars
import functools
import logging
from newrelic.api.transaction import current_transaction

_logger = logging.getLogger(__name__)
custom_attr_context_var = contextvars.ContextVar("custom_attr_context_var", default={})


class WithLlmCustomAttributes(object):
    def __init__(self, custom_attr_dict):
        transaction = current_transaction()
        if not custom_attr_dict or not isinstance(custom_attr_dict, dict):
            raise TypeError("custom_attr_dict must be a non-empty dictionary. Received type: %s" % type(custom_attr_dict))

        # Add "llm." prefix to all keys in attribute dictionary
        context_attrs = {k if k.startswith("llm.") else f"llm.{k}": v for k, v in custom_attr_dict.items()}

        self.attr_dict = context_attrs
        self.transaction = transaction

    def __enter__(self):
        if not self.transaction:
            _logger.warning("WithLlmCustomAttributes must be called within the scope of a transaction.")
            return self

        token = custom_attr_context_var.set(self.attr_dict)
        self.transaction._custom_attr_context_var = custom_attr_context_var
        return token

    def __exit__(self, exc, value, tb):
        if self.transaction:
            custom_attr_context_var.set(None)
            self.transaction._custom_attr_context_var = custom_attr_context_var

