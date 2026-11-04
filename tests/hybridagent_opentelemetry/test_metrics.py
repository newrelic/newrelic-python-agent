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


# Tests for the push OpenTelemetry metric instruments:
# - Counter
# - UpDownCounter
# - Histogram

from testing_support.validators.validate_otel_dimensional_metrics import validate_otel_dimensional_metrics


@validate_otel_dimensional_metrics(counter_expected=[(4, {"attribute_key": "attribute_value"}), (5, {})])
def test_counter(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(
        name="test_counter",
        description="A test counter",
        unit="1",
    )
    counter.add(2)
    counter.add(4, {"attribute_key": "attribute_value"})
    counter.add(3)


@validate_otel_dimensional_metrics(counter_expected=[(3.75, {})])
def test_counter_float_values(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(name="test_counter_float_values")
    counter.add(1.5)
    counter.add(2.25)


@validate_otel_dimensional_metrics(counter_expected=[(4, {"route": "/a"}), (2, {"route": "/b"}), (5, {"route": "/c"})])
def test_counter_multiple_attribute_sets(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(name="test_counter_multiple_attribute_sets")
    counter.add(1, {"route": "/a"})
    counter.add(2, {"route": "/b"})
    counter.add(3, {"route": "/a"})
    counter.add(5, {"route": "/c"})


MIXED_TYPE_ATTRIBUTES = {
    "string_attribute": "value",
    "int_attribute": 7,
    "float_attribute": 1.5,
    "bool_attribute": True,
    "sequence_attribute": ("a", "b"),
}


@validate_otel_dimensional_metrics(counter_expected=[(1, MIXED_TYPE_ATTRIBUTES)])
def test_counter_attribute_value_types(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(name="test_counter_attribute_value_types")
    counter.add(1, MIXED_TYPE_ATTRIBUTES)


@validate_otel_dimensional_metrics(counter_expected=[(0, {})])
def test_counter_add_zero(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(name="test_counter_add_zero")
    counter.add(0)


# The SDK drops negative and non-finite amounts on a Counter.
@validate_otel_dimensional_metrics(counter_expected=[(2, {})])
def test_counter_invalid_values(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(name="test_counter_invalid_values")
    counter.add(-1)
    counter.add(float("inf"))
    counter.add(float("nan"))
    counter.add(2)


@validate_otel_dimensional_metrics(counter_expected=[(3, {}), (-2, {"attribute_key": "attribute_value"})])
def test_up_down_counter(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    up_down_counter = meter.create_up_down_counter(
        name="test_up_down_counter", description="A test up down counter", unit="1"
    )
    up_down_counter.add(5)
    up_down_counter.add(4, {"attribute_key": "attribute_value"})
    up_down_counter.add(-2)
    up_down_counter.add(-6, {"attribute_key": "attribute_value"})


@validate_otel_dimensional_metrics(counter_expected=[(-3, {})])
def test_up_down_counter_goes_negative(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    up_down_counter = meter.create_up_down_counter(name="test_up_down_counter_goes_negative")
    up_down_counter.add(-3)


@validate_otel_dimensional_metrics(counter_expected=[(1.25, {})])
def test_up_down_counter_float_values(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    up_down_counter = meter.create_up_down_counter(name="test_up_down_counter_float_values")
    up_down_counter.add(1.5)
    up_down_counter.add(-0.25)


@validate_otel_dimensional_metrics(histogram_expected=[(3, 7, 1, 4, {"attribute_key": "attribute_value"})])
def test_histogram(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    histogram = meter.create_histogram(name="test_histogram", description="A test histogram", unit="ms")
    histogram.record(1, {"attribute_key": "attribute_value"})
    histogram.record(2, {"attribute_key": "attribute_value"})
    histogram.record(4, {"attribute_key": "attribute_value"})


@validate_otel_dimensional_metrics(histogram_expected=[(2, 4, 1, 3, {"route": "/a"}), (1, 10, 10, 10, {"route": "/b"})])
def test_histogram_multiple_attribute_sets(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    histogram = meter.create_histogram(name="test_histogram_multiple_attribute_sets")
    histogram.record(1, {"route": "/a"})
    histogram.record(3, {"route": "/a"})
    histogram.record(10, {"route": "/b"})


# The SDK drops negative and non-finite amounts on a Histogram.
@validate_otel_dimensional_metrics(histogram_expected=[(1, 3, 3, 3, {})])
def test_histogram_invalid_values(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    histogram = meter.create_histogram(name="test_histogram_invalid_values")
    histogram.record(-1)
    histogram.record(float("inf"))
    histogram.record(float("nan"))
    histogram.record(3)


# The same instrument name under two meters stays two separate metrics, one per scope.
# The validator doesn't record the scope, so only the values are checked.
@validate_otel_dimensional_metrics(counter_expected=[(1, {}), (2, {})])
def test_multiple_meters(meter_provider):
    meter_a = meter_provider.get_meter("test_meter_a", version="1.0")
    meter_b = meter_provider.get_meter("test_meter_b", version="2.0")
    meter_a.create_counter(name="test_counter_multiple_meters").add(1)
    meter_b.create_counter(name="test_counter_multiple_meters").add(2)
