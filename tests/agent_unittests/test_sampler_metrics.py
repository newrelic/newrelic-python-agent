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
import os
import platform

import pytest
from testing_support.fixtures import override_generic_settings

from newrelic.core.config import global_settings
from newrelic.packages import six
from newrelic.samplers.cpu_usage import cpu_usage_data_source
from newrelic.samplers.gc_data import garbage_collector_data_source
from newrelic.samplers.memory_usage import memory_usage_data_source

settings = global_settings()


@pytest.fixture
def gc_data_source():
    sampler = garbage_collector_data_source(settings=())["factory"](environ=())
    sampler.start()
    yield sampler
    sampler.stop()


@pytest.fixture
def cpu_data_source():
    sampler = cpu_usage_data_source(settings=())["factory"](environ=())
    sampler.start()
    yield sampler
    sampler.stop()


@pytest.fixture
def memory_data_source():
    sampler = memory_usage_data_source(settings=())["factory"](environ=())
    yield sampler


PID = os.getpid()

if six.PY2:
    EXPECTED_GC_METRICS = (
        "GC/objects/%d/all" % PID,
        "GC/objects/%d/generation/0" % PID,
        "GC/objects/%d/generation/1" % PID,
        "GC/objects/%d/generation/2" % PID,
    )
else:
    EXPECTED_GC_METRICS = (
        "GC/objects/%d/all" % PID,
        "GC/objects/%d/generation/0" % PID,
        "GC/objects/%d/generation/1" % PID,
        "GC/objects/%d/generation/2" % PID,
        "GC/collections/%d/all" % PID,
        "GC/collections/%d/0" % PID,
        "GC/collections/%d/1" % PID,
        "GC/collections/%d/2" % PID,
        "GC/collected/%d/all" % PID,
        "GC/collected/%d/0" % PID,
        "GC/collected/%d/1" % PID,
        "GC/collected/%d/2" % PID,
        "GC/uncollectable/%d/all" % PID,
        "GC/uncollectable/%d/0" % PID,
        "GC/uncollectable/%d/1" % PID,
        "GC/uncollectable/%d/2" % PID,
        "GC/time/%d/all" % PID,
        "GC/time/%d/0" % PID,
        "GC/time/%d/1" % PID,
        "GC/time/%d/2" % PID,
    )


@pytest.mark.xfail(
    platform.python_implementation() == "PyPy",
    reason="Not implemented on PyPy yet",
    strict=True,
    raises=AssertionError,
)
@pytest.mark.parametrize("top_object_count_limit", (1, 0))
def test_gc_metrics_collection(gc_data_source, top_object_count_limit):
    @override_generic_settings(
        settings,
        {
            "gc_runtime_metrics.enabled": True,
            "gc_runtime_metrics.top_object_count_limit": top_object_count_limit,
        },
    )
    def _test():
        gc.collect()
        metrics_table = set(m[0] for m in (gc_data_source() or ()))

        for metric in EXPECTED_GC_METRICS:
            assert metric in metrics_table

        # Verify object count by type metrics are recorded
        obj_metric_count = 0
        for metric in metrics_table:
            if metric.startswith("GC/objects/"):
                obj_metric_count += 1

        if top_object_count_limit > 0:
            assert obj_metric_count == 5, metrics_table
        else:
            assert obj_metric_count == 4, metrics_table

    _test()


@pytest.mark.skipif(
    platform.python_implementation() == "PyPy",
    reason="GC Metrics are always disabled on PyPy",
)
@pytest.mark.parametrize("enabled", (True, False))
def test_gc_metrics_config(gc_data_source, enabled):
    @override_generic_settings(settings, {"gc_runtime_metrics.enabled": enabled})
    def _test():
        assert gc_data_source.enabled == enabled

    _test()


EXPECTED_CPU_METRICS = (
    "CPU/User Time",
    "CPU/User/Utilization",
    "CPU/System Time",
    "CPU/System/Utilization",
    "CPU/Total Time",
    "CPU/Total/Utilization",
)


def test_cpu_metrics_collection(cpu_data_source):
    metrics_table = set(m[0] for m in (cpu_data_source() or ()))

    for metric in EXPECTED_CPU_METRICS:
        assert metric in metrics_table


EXPECTED_MEMORY_METRICS = (
    "Memory/Physical",
    "Memory/Physical/%d" % PID,
    "Memory/Physical/Utilization",
    "Memory/Physical/Utilization/%d" % PID,
)


def test_memory_metrics_collection(memory_data_source):
    metrics_table = set(m[0] for m in (memory_data_source() or ()))

    for metric in EXPECTED_MEMORY_METRICS:
        assert metric in metrics_table
