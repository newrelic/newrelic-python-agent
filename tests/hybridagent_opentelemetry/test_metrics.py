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




