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

import functools
import logging

from newrelic.api.time_trace import TimeTrace, current_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.async_wrapper import async_wrapper as get_async_wrapper
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object
from newrelic.core.function_node import FunctionNode

_logger = logging.getLogger(__name__)


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

        context_attrs = prefixed_attr_dict if prefixed_attr_dict else custom_attr_dict

        self.attr_dict = context_attrs
        self.transaction = transaction

    def __enter__(self):
        if not self.transaction:
            _logger.warning("WithLlmCustomAttributes must be called within the scope of a transaction.")
            return self

        self.transaction._llm_context_attrs = self.attr_dict
        return self

    def __exit__(self, exc, value, tb):
        if self.transaction:
            self.transaction._llm_context_attrs = None
