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
import logging

from newrelic.api.transaction import current_transaction

_logger = logging.getLogger(__name__)
custom_attr_context_var = contextvars.ContextVar("custom_attr_context_var", default={})


class WithLlmCustomAttributes(object):
    def __init__(self, custom_attr_dict):
        transaction = current_transaction()
        if not isinstance(custom_attr_dict, dict) or custom_attr_dict is None:
            raise TypeError("custom_attr_dict must be a dictionary. Received type: %s" % type(custom_attr_dict))

        # Add "llm." prefix to all keys in attribute dictionary
        prefixed_attr_dict = {}
        for k, v in custom_attr_dict.items():
            if not k.startswith("llm."):
                _logger.warning("Invalid attribute name %s. Renamed to llm.%s." % (k, k))
                prefixed_attr_dict["llm." + k] = v

        finalized_attrs = prefixed_attr_dict if prefixed_attr_dict else custom_attr_dict

        self.attr_dict = finalized_attrs
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
