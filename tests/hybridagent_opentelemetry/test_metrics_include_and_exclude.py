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
    (3.5, {"attribute_key3": "attribute_value3"}),
]

# Use three counters, counter1, counter2, and counter3
# As of now, the include list is a no-op
@pytest.mark.parametrize(
    "excluded_metrics,included_metrics,expected_sent_count",
    [
        (["counter1", "counter2", "counter3"], [], None), # Exclude all three counters
        (["counter1", "counter2", "counter3"], ["counter1", "counter2", "counter3"], None),   # Excludes all three counters
        ([], ["counter1", "counter2", "counter3"], [expected_counter1, expected_counter2, expected_counter3]),     # Includes all three counters
        ([], ["counter1"], [expected_counter1, expected_counter2, expected_counter3]),     # Includes all three counters
        (["counter1"], [], [expected_counter2, expected_counter3]),     # Excludes counter1
        (["counter1", "counter3"], [], [expected_counter2]),   # Excludes counter1 and counter3
    ],
    ids=[
        "exclude_all",
        "exclude_all_with_include_all",
        "include_all",
        "include_all_with_include_counter1",
        "exclude_counter1",
        "exclude_counter1_and_counter3",
    ]
)
def test_include_and_exclude_metrics(meter_provider, excluded_metrics, included_metrics, expected_sent_count):
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
    def run_test():
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
            name="counter3",
        )
        counter3.add(0.5, {"attribute_key3": "attribute_value3"})
        counter3.add(3.0, {"attribute_key3": "attribute_value3"})

    run_test()




