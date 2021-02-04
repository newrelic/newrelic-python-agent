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
from newrelic.samplers.cpu_usage import cpu_usage_data_source


@pytest.fixture
def data_source():
    sampler = cpu_usage_data_source(settings=())["factory"](environ=())
    sampler.start()
    yield sampler
    sampler.stop()


EXPECTED_METRICS = (
    "CPU/User Time",
    "CPU/User/Utilization",
    "CPU/System Time",
    "CPU/System/Utilization",
    "CPU/Total Time",
    "CPU/Total/Utilization",
)


def test_cpu_metrics_collection(data_source):
    metrics_table = set(m[0] for m in (data_source() or ()))

    for metric in EXPECTED_METRICS:
        assert metric in metrics_table
