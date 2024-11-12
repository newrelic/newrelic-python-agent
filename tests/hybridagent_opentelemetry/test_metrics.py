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

from opentelemetry.metrics import Observation, get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

provider = MeterProvider()
set_meter_provider(provider)


# Counter
@validate_transaction_metrics(
    name="test_metrics:test_counter_meter",
    custom_metrics=[
        ("OtelMeter/CounterMeter/counter", 4.5),
        ("OtelMeter/CounterMeter/0.1.2", 1),
    ],
    background_task=True,
)
@background_task()
def test_counter_meter():
    meter = get_meter_provider().get_meter("CounterMeter", "0.1.2")
    counter = meter.create_counter("counter")
    counter.add(1)
    counter.add(3)
    counter.add(0.5)


# ObservableCounter
@validate_transaction_metrics(
    name="test_metrics:test_observable_counter_meter",
    custom_metrics=[
        ("OtelMeter/ObservableCounterMeter/observable_counter", 10),
        ("OtelMeter/ObservableCounterMeter/1.2.3", 1),
    ],
    background_task=True,
)
@background_task()
def test_observable_counter_meter():
    def _count_generator():
        for i in range(5):
            yield Observation(i)

    meter = get_meter_provider().get_meter("ObservableCounterMeter", "1.2.3")
    meter.create_observable_counter("observable_counter", [_count_generator])


# UpDownCounter
@validate_transaction_metrics(
    name="test_metrics:test_updowncounter_meter",
    custom_metrics=[
        ("OtelMeter/UpDownCounterMeter/updown_counter", -4),
        ("OtelMeter/UpDownCounterMeter/2.3.4", 1),
    ],
    background_task=True,
)
@background_task()
def test_updowncounter_meter():
    meter = get_meter_provider().get_meter("UpDownCounterMeter", "2.3.4")
    updown_counter = meter.create_up_down_counter("updown_counter")
    updown_counter.add(1)
    updown_counter.add(-5)


# ObservableUpDownCounter
@validate_transaction_metrics(
    name="test_metrics:test_observable_updowncounter_meter",
    custom_metrics=[
        ("OtelMeter/ObservableUpDownCounterMeter/observable_updown_counter", -10),
        ("OtelMeter/ObservableUpDownCounterMeter/3.4.5", 1),
    ],
    background_task=True,
)
@background_task()
def test_observable_updowncounter_meter():
    def _count_generator():
        for i in range(5):
            yield Observation(-i)

    meter = get_meter_provider().get_meter("ObservableUpDownCounterMeter", "3.4.5")
    meter.create_observable_up_down_counter("observable_updown_counter", [_count_generator])


# Histogram
@validate_transaction_metrics(
    name="test_metrics:test_histogram_meter",
    custom_metrics=[
        ("OtelMeter/HistogramMeter/histogram", 4),
        ("OtelMeter/HistogramMeter/5.6.7", 1),
    ],
    background_task=True,
)
@background_task()
def test_histogram_meter():
    meter = get_meter_provider().get_meter("HistogramMeter", "5.6.7")
    histogram = meter.create_histogram("histogram")
    histogram.record(99.9)
    histogram.record(0.1)
    histogram.record(75)
    histogram.record(25)


# ObservableGauge
@validate_transaction_metrics(
    name="test_metrics:test_gauge_meter",
    custom_metrics=[
        ("OtelMeter/GaugeMeter/gauge", 5),
        ("OtelMeter/GaugeMeter/6.7.8", 1),
    ],
    background_task=True,
)
@background_task()
def test_gauge_meter():
    def _gauge_generator():
        for i in range(5):
            yield Observation(i)

    meter = get_meter_provider().get_meter("GaugeMeter", "6.7.8")
    meter.create_observable_gauge("gauge", [_gauge_generator])
