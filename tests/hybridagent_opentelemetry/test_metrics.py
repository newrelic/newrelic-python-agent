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


@validate_otel_dimensional_metrics(
    counter_expected=[("test_counter", 4, {"attribute_key": "attribute_value"}), ("test_counter", 5, {})]
)
def test_counter(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(name="test_counter", description="A test counter", unit="1")
    counter.add(2)
    counter.add(4, {"attribute_key": "attribute_value"})
    counter.add(3)


@validate_otel_dimensional_metrics(counter_expected=[("test_counter_float_values", 3.75, {})])
def test_counter_float_values(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(name="test_counter_float_values")
    counter.add(1.5)
    counter.add(2.25)


# The SDK drops negative and non-finite amounts on a Counter.
@validate_otel_dimensional_metrics(counter_expected=[("test_counter_invalid_values", 2, {})])
def test_counter_invalid_values(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(name="test_counter_invalid_values")
    counter.add(-1)
    counter.add(float("inf"))
    counter.add(float("nan"))
    counter.add(2)


@validate_otel_dimensional_metrics(
    counter_expected=[
        ("test_up_down_counter", 3, {}),
        ("test_up_down_counter", -2, {"attribute_key": "attribute_value"}),
    ]
)
def test_up_down_counter(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    up_down_counter = meter.create_up_down_counter(
        name="test_up_down_counter", description="A test up down counter", unit="1"
    )
    up_down_counter.add(5)
    up_down_counter.add(-2)
    up_down_counter.add(4, {"attribute_key": "attribute_value"})
    up_down_counter.add(-6, {"attribute_key": "attribute_value"})


# The SDK drops non-finite amounts on an UpDownCounter.
@validate_otel_dimensional_metrics(counter_expected=[("test_up_down_counter_invalid_values", 2, {})])
def test_up_down_counter_invalid_values(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    up_down_counter = meter.create_up_down_counter(name="test_up_down_counter_invalid_values")
    up_down_counter.add(float("inf"))
    up_down_counter.add(float("nan"))
    up_down_counter.add(2)


@validate_otel_dimensional_metrics(
    histogram_expected=[
        ("test_histogram", 2, 30, 10, 20, {}),
        ("test_histogram", 3, 7, 1, 4, {"attribute_key": "attribute_value"}),
    ]
)
def test_histogram(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    histogram = meter.create_histogram(name="test_histogram", description="A test histogram", unit="ms")
    histogram.record(10)
    histogram.record(20)
    histogram.record(1, {"attribute_key": "attribute_value"})
    histogram.record(2, {"attribute_key": "attribute_value"})
    histogram.record(4, {"attribute_key": "attribute_value"})


# The SDK drops negative and non-finite amounts on a Histogram.
@validate_otel_dimensional_metrics(histogram_expected=[("test_histogram_invalid_values", 1, 3, 3, 3, {})])
def test_histogram_invalid_values(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    histogram = meter.create_histogram(name="test_histogram_invalid_values")
    histogram.record(-1)
    histogram.record(float("inf"))
    histogram.record(float("nan"))
    histogram.record(3)
