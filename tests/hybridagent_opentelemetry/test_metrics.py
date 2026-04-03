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

# import pytest
from testing_support.validators.validate_dimensional_metrics_outside_transaction import (
    validate_dimensional_metrics_outside_transaction,
)

# TODO:
# test all metric types
# test counter with negative value

@validate_dimensional_metrics_outside_transaction([("example_counter", {"attr_key": "attr_value"}, 5)])
def test_counter(meter):
    # breakpoint()
    counter_instance = meter.create_counter("example_counter")
    
    counter_instance.add(1, {"attr_key": "attr_value"})
    counter_instance.add(4)
    
    
    
