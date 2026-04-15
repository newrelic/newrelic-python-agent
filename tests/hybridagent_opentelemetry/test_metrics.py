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

import pytest
import time
# from opentelemetry import metrics
from opentelemetry.metrics import Observation
from newrelic.api.background_task import background_task
# from newrelic.core.application import Application
from newrelic.api.application import application_instance
from newrelic.core.config import global_settings
from testing_support.validators.validate_dimensional_metrics_outside_transaction import (
    validate_dimensional_metrics_outside_transaction,
)
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.fixtures import override_generic_settings #reset_core_stats_engine

settings = global_settings()

# TODO:
# test create_observable_counter, histogram, observable_gauge, observable_up_down_counter, gauge
# test failing tests

# @reset_core_stats_engine()
@validate_transaction_metrics(
    "test_metrics:test_counter",
    background_task=True,
    dimensional_metrics=[
        ("example_counter", {"attr_key": "attr_value", "description": "Example Hybrid Agent Counter", "unit": "vibes"}, 4.4),
        ("example_counter", {"description": "Example Hybrid Agent Counter", "unit": "vibes"}, 2),
    ],
)
@background_task()
def test_counter(meter):
    # FROM Metric SELECT * WHERE metricName='example_counter'
    counter_instance = meter.create_counter(
        "example_counter",
        description="Example Hybrid Agent Counter",
        unit="vibes",
    )
    
    counter_instance.add(1, {"attr_key": "attr_value"})
    counter_instance.add(2)
    counter_instance.add(3.4, {"attr_key": "attr_value"})
    counter_instance.add(0)


# @reset_core_stats_engine()
@validate_dimensional_metrics_outside_transaction(
    [
        ("example_counter_outside_transaction", {"attr_key": "attr_value"}, 3.2),
        ("example_counter_outside_transaction", None, 4),
    ],
    opentelemetry=True,
)
def test_counter_outside_transaction(meter):
    # FROM Metric SELECT * WHERE metricName='example_counter_outside_transaction'
    counter_instance = meter.create_counter("example_counter_outside_transaction")
    
    counter_instance.add(1, {"attr_key": "attr_value"})
    counter_instance.add(4)
    counter_instance.add(2.2, {"attr_key": "attr_value"})


@pytest.mark.parametrize(
    "value",
    [
        -2,
        "2",
        "two",
    ],
)
# @reset_core_stats_engine()
@background_task()
def test_counter_with_invalid_values(meter, value):
    counter_instance = meter.create_counter("example_counter_invalid")
    with pytest.raises(ValueError):
        counter_instance.add(value)


# @reset_core_stats_engine()
@validate_transaction_metrics(
    "test_metrics:test_up_down_counter",
    background_task=True,
    dimensional_metrics=[
        ("example_up_down_counter", {"attr_key": "attr_value"}, -2.4),
        ("example_up_down_counter", None, -2),
    ],
)
@background_task()
def test_up_down_counter(meter):
    # FROM Metric SELECT * WHERE metricName='example_up_down_counter'
    counter_instance = meter.create_up_down_counter("example_up_down_counter")
    
    counter_instance.add(1, {"attr_key": "attr_value"})
    counter_instance.add(-2)
    counter_instance.add(-3.4, {"attr_key": "attr_value"})
    counter_instance.add(0)


# @reset_core_stats_engine()
@validate_dimensional_metrics_outside_transaction(
    [
        ("example_up_down_counter_outside_transaction", {"attr_key": "attr_value"}, 2.4),
        ("example_up_down_counter_outside_transaction", None, 4),
    ],
    opentelemetry=True,
)
def test_up_down_counter_outside_transaction(meter):
    # FROM Metric SELECT * WHERE metricName='example_up_down_counter_outside_transaction'
    counter_instance = meter.create_up_down_counter("example_up_down_counter_outside_transaction")
    
    counter_instance.add(3.4, {"attr_key": "attr_value"})
    counter_instance.add(4)
    counter_instance.add(-1, {"attr_key": "attr_value"})


@pytest.mark.parametrize(
    "value",
    [
        "2",
        "two",
    ],
)
# @reset_core_stats_engine()
@background_task()
def test_up_down_counter_with_invalid_values(meter, value):
    counter_instance = meter.create_up_down_counter("example_up_down_counter_invalid")
    with pytest.raises(ValueError):
        counter_instance.add(1)
        counter_instance.add(value)


# TODO: THIS IS ALSO WRONG.  THIS NEEDS TO BE A PULL METRIC.
# @reset_core_stats_engine()
@validate_transaction_metrics(
    "test_metrics:test_observable_counter",
    background_task=True,
    dimensional_metrics=[
        ("example_observable_counter", {"attr_key": "attr_value", "description": "Example Hybrid Agent Observable Counter", "unit": "async vibes"}, 42),
        ("example_observable_counter", {"description": "Example Hybrid Agent Observable Counter", "unit": "async vibes"}, 15),
    ],
)
@background_task()
def test_observable_counter(meter):
    # FROM Metric SELECT * WHERE metricName='example_observable_counter'
    def range_callback(options):
        for val in range(2, 20, 3):
            if val > 10:
                yield Observation(val, {"attr_key": "attr_value"})
            else:
                yield Observation(val)
                

    meter.create_observable_counter(
        "example_observable_counter",
        callbacks=[range_callback],
        description="Example Hybrid Agent Observable Counter",
        unit="async vibes",
    )


# TODO: THIS IS ALSO WRONG.  THIS NEEDS TO BE A PULL METRIC.
# @reset_core_stats_engine()
@validate_dimensional_metrics_outside_transaction(
    [
        ("example_observable_counter_outside_transaction",{"attr_key": "attr_value", "description": "Example Hybrid Agent Observable Counter", "unit": "async vibes"}, 1.0),
    ],
    opentelemetry=True,
)
def test_observable_counter_outside_transaction(meter):
    # FROM Metric SELECT * WHERE metricName='example_observable_counter_outside_transaction'
    def range_callback(options):
        list_of_floats = [x*0.1 for x in range(0,5)]
        for val in list_of_floats:
            yield Observation(val, {"attr_key": "attr_value"})

    meter.create_observable_counter(
        "example_observable_counter_outside_transaction",
        callbacks=[range_callback],
        description="Example Hybrid Agent Observable Counter",
        unit="async vibes",
    )

# Invalid callback functions
def _callback_with_negatives(options):
    for val in range(-20, 2, 3):
        yield Observation(val)

def _callback_without_observation_type(options):
    for val in range(-20, 2, 3):
        yield val
    
def _callback_with_strings(options):
    for val in ["one", "2!", "3"]:
        yield Observation(val)

def _callback_with_no_options_argument():
    for val in range(-20, 2, 3):
        yield Observation(val)


@pytest.mark.parametrize(
    "invalid_callback",
    [
        _callback_with_negatives,
        _callback_without_observation_type,
        _callback_with_strings,
        _callback_with_no_options_argument,
        "Just a string",
    ],
)
# @reset_core_stats_engine()
def test_observable_counter_with_invalid_callbacks(meter, invalid_callback):
    @background_task()
    def _test():
        with pytest.raises((ValueError, TypeError)):
            meter.create_observable_counter(
                "example_observable_counter_invalid",
                callbacks=[invalid_callback],
                description="Example Hybrid Agent Observable Counter",
                unit="async vibes",
            )
            
    _test()


# @reset_core_stats_engine()
@validate_transaction_metrics(
    "test_metrics:test_observable_up_down_counter",
    background_task=True,
    dimensional_metrics=[
        ("example_observable_up_down_counter", None, -22),
    ],
)
@background_task()
def test_observable_up_down_counter(meter):
    # FROM Metric SELECT * WHERE metricName='example_observable_up_down_counter'
    def range_callback(options):
        for val in range(-10, 2, 3):
            yield Observation(val)
                

    meter.create_observable_up_down_counter(
        "example_observable_up_down_counter",
        callbacks=[range_callback],
    )


# @reset_core_stats_engine()
@validate_dimensional_metrics_outside_transaction(
    [
        ("example_observable_up_down_counter_outside_transaction",{"attr_key": "attr_value", "description": "Example Hybrid Agent Observable Up Down Counter", "unit": "async vibes"}, 0.5),
    ],
    opentelemetry=True,
)
def test_observable_up_down_counter_outside_transaction(meter):
    # FROM Metric SELECT * WHERE metricName='example_observable_up_down_counter_outside_transaction'
    def range_callback(options):
        list_of_floats = [x*0.1 for x in range(0,10)]
        for index, val in enumerate(list_of_floats):
            if index % 2 == 0:
                val *= -1
            yield Observation(val, {"attr_key": "attr_value"})

    meter.create_observable_up_down_counter(
        "example_observable_up_down_counter_outside_transaction",
        callbacks=[range_callback],
        description="Example Hybrid Agent Observable Up Down Counter",
        unit="async vibes",
    )


@pytest.mark.parametrize(
    "invalid_callback",
    [
        _callback_without_observation_type,
        _callback_with_strings,
        _callback_with_no_options_argument,
        "Just a string",
    ],
)
# @reset_core_stats_engine()
def test_observable_up_down_counter_with_invalid_callbacks(meter, invalid_callback):
    @background_task()
    def _test():
        with pytest.raises((ValueError, TypeError)):
            meter.create_observable_up_down_counter(
                "example_observable_up_down_counter_invalid",
                callbacks=[invalid_callback],
                description="Example Hybrid Agent Observable Up Down Counter",
                unit="async vibes",
            )
            
    _test()


# @pytest.fixture
# def observable_gauge_function():
#     for val in range(10):
#         yield Observation(val, {"attr_key": "attr_value"}) 
    

# @reset_core_stats_engine()
@validate_transaction_metrics(
    "test_metrics:test_observable_gauge",
    background_task=True,
    dimensional_metrics=[
        (
            "example_observable_gauge_function/attr_key/attr_value",
            {
                "description": "Example Hybrid Agent Observable Gauge",
                "unit": "async vibes",
            },
            1,
        ),
    ],
)
@background_task()
# @override_generic_settings(settings, {"developer_mode": True, "license_key": "**NOT A LICENSE KEY**", "opentelemetry.enabled": True})
def test_observable_gauge(meter):
    # TODO: verify this
    # FROM Metric SELECT * WHERE metricName='example_observable_gauge'
    def observable_gauge_function(options):
        for val in range(1,2):
            yield Observation(val, {"attr_key": "attr_value"}) 
    # def range_callback(options):
    #     for val in range(10):
    #         yield Observation(val, {"attr_key": "attr_value"})
                
    meter.create_observable_gauge(
        "example_observable_gauge",
        callbacks=[observable_gauge_function],
        description="Example Hybrid Agent Observable Gauge",
        unit="async vibes",
    )
    time.sleep(140)

    # app = Application("Python Agent Test (Hybrid Agent, Observable Gauge)")
    # app.connect_to_data_collector(None)
    # settings.event_harvest_config.allowlist = frozenset(("custom_event_data",))
    # app._stats_engine.reset_stats(settings)
    
    # def observable_gauge_function(options):
    #     for val in range(1,2):
    #         yield Observation(val, {"attr_key": "attr_value"}) 
                
    # meter.create_observable_gauge(
    #     "example_observable_gauge",
    #     callbacks=[observable_gauge_function],
    #     description="Example Hybrid Agent Observable Gauge",
    #     unit="async vibes",
    # )

    # app = application_instance()

    # app.harvest()
    # app.harvest()
    # app.harvest()
    # app.harvest()   # THIS ONLY HAS THE CALLBACK AFTER THE FUNCTION COMPLETES
    # assert app._stats_engine.opentelemetry_stats_table
    # # assert ("example_observable_gauge_function/attr_key/attr_value", frozenset({("description", "Example Hybrid Agent Observable Gauge"), ("unit", "async vibes")})) in app._stats_engine.dimensional_stats_table
    # assert app._stats_engine.metrics_count()


# @pytest.mark.parametrize(
#     "invalid_callback",
#     [
#         _callback_without_observation_type,
#         _callback_with_strings,
#         _callback_with_no_options_argument,
#         "Just a string",
#     ],
# )
# @reset_core_stats_engine()
# def test_observable_gauge_with_invalid_callbacks(meter, invalid_callback):
#     @background_task()
#     def _test():
#         with pytest.raises((ValueError, TypeError)):
#             meter.create_observable_gauge(
#                 "example_observable_gauge",
#                 callbacks=[invalid_callback],
#                 description="Example Hybrid Agent Observable Gauge",
#                 unit="async vibes",
#             )
            
#     _test()

