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
    from newrelic.packages.opentelemetry_proto.logs_pb2 import (
        LogRecord,
        ResourceLogs,
        ScopeLogs,
    )
    from newrelic.packages.opentelemetry_proto.metrics_pb2 import (
        AggregationTemporality,
        Metric,
        MetricsData,
        NumberDataPoint,
        ResourceMetrics,
        ScopeMetrics,
        Sum,
        Summary,
        SummaryDataPoint,
    )
    from newrelic.packages.opentelemetry_proto.resource_pb2 import Resource

    AGGREGATION_TEMPORALITY_DELTA = AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA
    ValueAtQuantile = SummaryDataPoint.ValueAtQuantile

    otlp_encode = lambda payload: payload.SerializeToString()
    OTLP_CONTENT_TYPE = "application/x-protobuf"

except ImportError:
    from newrelic.common.encoding_utils import json_encode

    def otlp_encode(*args, **kwargs):
        _logger.warn(
            "Using OTLP integration while protobuf is not installed. This may result in larger payload sizes and data loss."
        )
        return json_encode(*args, **kwargs)

    Resource = dict
    ValueAtQuantile = dict
    AnyValue = dict
    KeyValue = dict
    NumberDataPoint = dict
    SummaryDataPoint = dict
    Sum = dict
    Summary = dict
    Metric = dict
    MetricsData = dict
    ScopeMetrics = dict
    ResourceMetrics = dict
    AGGREGATION_TEMPORALITY_DELTA = 1
    ResourceLogs = dict
    ScopeLogs = dict
    LogRecord = dict
    OTLP_CONTENT_TYPE = "application/json"


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


def create_resource(attributes=None):
    attributes = attributes or {"instrumentation.provider": "nr_performance_monitoring"}
    return Resource(attributes=create_key_values_from_iterable(attributes))
