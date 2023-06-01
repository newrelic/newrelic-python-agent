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

"""This module provides common utilities for interacting with OTLP protocol buffers."""

import logging
_logger = logging.getLogger(__name__)

try:
    from newrelic.packages.opentelemetry_proto.common_pb2 import AnyValue, KeyValue
except ImportError:
    create_key_value, create_key_values_from_iterable = None, None
else:
    def create_key_value(key, value):
        if isinstance(value, bool):
            return KeyValue(key=key, value=AnyValue(bool_value=value))
        elif isinstance(value, int):
            return KeyValue(key=key, value=AnyValue(int_value=value))
        elif isinstance(value, float):
            return KeyValue(key=key, value=AnyValue(double_value=value))
        elif isinstance(value, str):
            return KeyValue(key=key, value=AnyValue(string_value=value))
        # Technically AnyValue accepts array, kvlist, and bytes however, since
        # those are not valid custom attribute types according to our api spec,
        # we will not bother to support them here either.
        else:
            _logger.warn("Unsupported attribute value type %s: %s." % (key, value))

    def create_key_values_from_iterable(iterable):
        if isinstance(iterable, dict):
            iterable = iterable.items()

        # The create_key_value list may return None if the value is an unsupported type
        # so filter None values out before returning.
        return list(
            filter(
                lambda i: i is not None,
                (create_key_value(key, value) for key, value in iterable),
            )
        )
