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


# Tests for the pull OpenTelemetry metric instruments:
# - ObservableCounter
# - ObservableUpDownCounter
# - ObservableGauge

from opentelemetry.metrics import Observation
from testing_support.validators.validate_otel_dimensional_metrics import validate_otel_dimensional_metrics


@validate_otel_dimensional_metrics(
    counter_expected=[
        ("test_observable_counter", 10, {}),
        ("test_observable_counter", 4, {"attribute_key": "attribute_value"}),
    ]
)
def test_observable_counter(meter_provider):
    def callback(options):
        return [Observation(10), Observation(4, {"attribute_key": "attribute_value"})]

    meter = meter_provider.get_meter("test_meter")
    meter.create_observable_counter(
        name="test_observable_counter", callbacks=[callback], description="A test observable counter", unit="s"
    )


@validate_otel_dimensional_metrics(counter_expected=[("test_observable_counter_float_values", 3.75, {})])
def test_observable_counter_float_values(meter_provider):
    def callback(options):
        return [Observation(3.75)]

    meter = meter_provider.get_meter("test_meter")
    meter.create_observable_counter(name="test_observable_counter_float_values", callbacks=[callback])


# The SDK drops non-finite values on an ObservableCounter, but keeps negative ones.
@validate_otel_dimensional_metrics(
    counter_expected=[
        ("test_observable_counter_invalid_values", 2, {}),
        ("test_observable_counter_invalid_values", -1, {"attribute_key": "negative"}),
    ]
)
def test_observable_counter_invalid_values(meter_provider):
    def callback(options):
        return [
            Observation(2),
            Observation(-1, {"attribute_key": "negative"}),
            Observation(float("inf"), {"attribute_key": "inf"}),
            Observation(float("nan"), {"attribute_key": "nan"}),
        ]

    meter = meter_provider.get_meter("test_meter")
    meter.create_observable_counter(name="test_observable_counter_invalid_values", callbacks=[callback])


@validate_otel_dimensional_metrics(
    counter_expected=[
        ("test_observable_up_down_counter", 3, {}),
        ("test_observable_up_down_counter", -2, {"attribute_key": "attribute_value"}),
    ]
)
def test_observable_up_down_counter(meter_provider):
    def callback(options):
        return [Observation(3), Observation(-2, {"attribute_key": "attribute_value"})]

    meter = meter_provider.get_meter("test_meter")
    meter.create_observable_up_down_counter(
        name="test_observable_up_down_counter",
        callbacks=[callback],
        description="A test observable up down counter",
        unit="s",
    )


# The SDK drops non-finite values on an ObservableUpDownCounter.
@validate_otel_dimensional_metrics(counter_expected=[("test_observable_up_down_counter_invalid_values", 2, {})])
def test_observable_up_down_counter_invalid_values(meter_provider):
    def callback(options):
        return [
            Observation(2),
            Observation(float("inf"), {"attribute_key": "inf"}),
            Observation(float("nan"), {"attribute_key": "nan"}),
        ]

    meter = meter_provider.get_meter("test_meter")
    meter.create_observable_up_down_counter(name="test_observable_up_down_counter_invalid_values", callbacks=[callback])


@validate_otel_dimensional_metrics(
    gauge_expected=[
        ("test_observable_gauge", 72, {}),
        ("test_observable_gauge", 68, {"attribute_key": "attribute_value"}),
    ]
)
def test_observable_gauge(meter_provider):
    def callback(options):
        return [Observation(72), Observation(68, {"attribute_key": "attribute_value"})]

    meter = meter_provider.get_meter("test_meter")
    meter.create_observable_gauge(
        name="test_observable_gauge", callbacks=[callback], description="A test observable gauge", unit="Cel"
    )


# The SDK drops non-finite values on an ObservableGauge.
@validate_otel_dimensional_metrics(gauge_expected=[("test_observable_gauge_invalid_values", 2, {})])
def test_observable_gauge_invalid_values(meter_provider):
    def callback(options):
        return [
            Observation(2),
            Observation(float("inf"), {"attribute_key": "inf"}),
            Observation(float("nan"), {"attribute_key": "nan"}),
        ]

    meter = meter_provider.get_meter("test_meter")
    meter.create_observable_gauge(name="test_observable_gauge_invalid_values", callbacks=[callback])
