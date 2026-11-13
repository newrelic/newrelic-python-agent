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

from newrelic.core.config import global_settings
from newrelic.core.agent import agent_instance

from testing_support.fixtures import override_generic_settings
from testing_support.validators.validate_otel_dimensional_metrics import validate_otel_dimensional_metrics


expected_counter1 = [
    (5, {}),
]
expected_counter2 = [
    (5, {"attribute_key2": "attribute_value2"}),
    (7.5, {}),
]
expected_counter3 = [
    (4.5, {"attribute_key3": "attribute_value3"}),
]
expected_counter4 = [
    (1, {}),
]
expected_counter5 = [
    (10, {}),
]

@pytest.mark.parametrize(
    "excluded_metrics,included_metrics,expected_sent_count",
    [
        (set(), set(), [*expected_counter1, *expected_counter2]), # Exclude counter3, counter4, and counter5
        ({"counter1", "counter2", "OtherTransaction/SomeName"}, set(), None), # Exclude all five counters
        ({"counter1", "counter2", "OtherTransaction/SomeName"}, {"counter1", "counter2", "OtherTransaction/SomeName"}, None),   # Excludes all five counters
        (set(), {"counter1", "counter2", "OtherTransaction/SomeName", "MessageBroker/ServiceBus/PartyBus/Named/George", "HttpDispatcher"}, [*expected_counter1, *expected_counter2, *expected_counter3, *expected_counter4, *expected_counter5]),     # Includes all five counters
        (set(), {"counter1"}, [*expected_counter1, *expected_counter2]),     # Includes counter1 and counter2 (counter3, counter4, and counter5 are excluded internally)
        ({"counter1"}, set(), [*expected_counter2]),     # Excludes counter1, counter3, counter4, and counter5
        ({"counter1"}, {"OtherTransaction/SomeName"}, [*expected_counter2, *expected_counter3]),   # Excludes counter1, counter4, and counter5
        ({"counter1"}, {"MessageBroker/ServiceBus/PartyBus/Named/George"}, [*expected_counter2, *expected_counter4]),   # Excludes counter1, counter3, and counter5
        ({"counter1"}, {"HttpDispatcher"}, [*expected_counter2, *expected_counter5]),   # Excludes counter1, counter3, and counter4
        ({"*"}, set(), None),   # Exclude all five counters
        (set(), {"*"}, [*expected_counter1, *expected_counter2, *expected_counter3, *expected_counter4, *expected_counter5]),   # Include all five counters
        (set(), {"HttpDispatcher*"}, [*expected_counter1, *expected_counter2, *expected_counter5]),   # Include counter1, counter2, counter5
    ],
    ids=[
        "internal_exclude_counter3",
        "exclude_all",
        "exclude_all_with_include_all",
        "include_all",
        "include_counter1",
        "exclude_counter1",
        "exclude_counter1_with_include_counter3",
        "exclude_counter1_with_include_counter4",
        "exclude_counter1_with_include_counter5",
        "exclude_all_wildcard",
        "include_all_wildcard",
        "include_counter5_wildcard",
    ]
)
def test_include_and_exclude_metrics(excluded_metrics, included_metrics, expected_sent_count):
    """
    This test validates the include/exclude logic but it also ensures that the wildcarding
    within the NEW_RELIC_METRICS set does not have unintended side effects. Therefore, five
    counters are used:
    * counter1:
        This should always be included unless included in the user exclude list.
    * counter2:
        This should always be included unless included in the user exclude list.
    * OtherTransaction/SomeName:
        The internal exclude list contains `OtherTransaction/*`, which would by
        default exclude `OtherTransaction/SomeName` unless it is explicitly included
        in the user include list.
    * MessageBroker/ServiceBus/PartyBus/Named/George:
        The internal exclude list contains `MessageBroker/ServiceBus/*/Named/*`, which
        would by default exclude `MessageBroker/ServiceBus/PartyBus/Named/George`
        unless it is explicitly included in the user include list.
    * HttpDispatcher:
        The internal exclude list contains `HttpDispatcher`, which would by default
        exclude `HttpDispatcher` unless it is explicitly included in the user include list.
    """
    @override_generic_settings(
        global_settings(),
        {
            "opentelemetry.metrics.include": included_metrics,
            "opentelemetry.metrics.exclude": excluded_metrics,
        }
    )
    @validate_otel_dimensional_metrics(
        counter_expected=expected_sent_count
    )
    def _test():

        from opentelemetry.sdk.metrics import MeterProvider
        import opentelemetry.metrics._internal

        # Set up a new MeterProvider for each iteration of this test
        original_meter_provider = agent_instance()._meter_provider
        agent_instance()._meter_provider = None
        meter_provider = MeterProvider()
        opentelemetry.metrics._internal._METER_PROVIDER = meter_provider

        meter = meter_provider.get_meter("test_meter")
        counter1 = meter.create_counter(
            name="counter1",
        )
        counter1.add(2)
        counter1.add(3)

        counter2 = meter.create_counter(
            name="counter2",
        )
        counter2.add(5, {"attribute_key2": "attribute_value2"})
        counter2.add(7.5)

        counter3 = meter.create_counter(
            name="OtherTransaction/SomeName",
        )
        counter3.add(0.5, {"attribute_key3": "attribute_value3"})
        counter3.add(4.0, {"attribute_key3": "attribute_value3"})

        counter4 = meter.create_counter(
            name="MessageBroker/ServiceBus/PartyBus/Named/George",
        )
        counter4.add(1)

        counter5 = meter.create_counter(
            name="HttpDispatcher",
        )
        counter5.add(10)

        # Revert the MeterProvider to the original one
        agent_instance()._meter_provider = original_meter_provider

    _test()



