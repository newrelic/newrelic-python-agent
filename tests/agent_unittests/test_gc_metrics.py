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

from newrelic.packages import six
from newrelic.samplers.gc_data import garbage_collector_data_source


@pytest.fixture
def data_source():
    sampler = garbage_collector_data_source(settings=())["factory"](environ=())
    sampler.start()
    yield sampler
    sampler.stop()


if six.PY2:
    EXPECTED_METRICS = (
        "GC/objects/all",
        "GC/objects/generation/0",
        "GC/objects/generation/1",
        "GC/objects/generation/2",
    )
else:
    EXPECTED_METRICS = (
        "GC/objects/all",
        "GC/objects/generation/0",
        "GC/objects/generation/1",
        "GC/objects/generation/2",
        "GC/stats/collections/all",
        "GC/stats/collections/generation/0",
        "GC/stats/collections/generation/1",
        "GC/stats/collections/generation/2",
        "GC/stats/collected/all",
        "GC/stats/collected/generation/0",
        "GC/stats/collected/generation/1",
        "GC/stats/collected/generation/2",
        "GC/stats/uncollectable/all",
        "GC/stats/uncollectable/generation/0",
        "GC/stats/uncollectable/generation/1",
        "GC/stats/uncollectable/generation/2",
    )


def test_gc_metrics_collection(data_source):
    metrics_table = dict(data_source() or ())

    for metric in EXPECTED_METRICS:
        assert metric in metrics_table
