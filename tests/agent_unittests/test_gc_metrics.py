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

import gc
import platform

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
        "GC/objects/0",
        "GC/objects/1",
        "GC/objects/2",
    )
else:
    EXPECTED_METRICS = (
        "GC/objects/all",
        "GC/objects/0",
        "GC/objects/1",
        "GC/objects/2",
        "GC/collections/all",
        "GC/collections/0",
        "GC/collections/1",
        "GC/collections/2",
        "GC/collected/all",
        "GC/collected/0",
        "GC/collected/1",
        "GC/collected/2",
        "GC/uncollectable/all",
        "GC/uncollectable/0",
        "GC/uncollectable/1",
        "GC/uncollectable/2",
        "GC/time/all",
        "GC/time/0",
        "GC/time/1",
        "GC/time/2",
    )


@pytest.mark.xfail(
    platform.python_implementation() == "PyPy",
    reason="Not implemented on PyPy yet",
    strict=True,
    raises=AssertionError,
)
def test_gc_metrics_collection(data_source):
    gc.collect()
    metrics_table = dict(data_source() or ())

    for metric in EXPECTED_METRICS:
        assert metric in metrics_table
