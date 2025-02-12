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

EXPECTED_GC_METRICS = (
    f"GC/objects/{PID}/all",
    f"GC/objects/{PID}/generation/0",
    f"GC/objects/{PID}/generation/1",
    f"GC/objects/{PID}/generation/2",
    f"GC/collections/{PID}/all",
    f"GC/collections/{PID}/0",
    f"GC/collections/{PID}/1",
    f"GC/collections/{PID}/2",
    f"GC/collected/{PID}/all",
    f"GC/collected/{PID}/0",
    f"GC/collected/{PID}/1",
    f"GC/collected/{PID}/2",
    f"GC/uncollectable/{PID}/all",
    f"GC/uncollectable/{PID}/0",
    f"GC/uncollectable/{PID}/1",
    f"GC/uncollectable/{PID}/2",
    f"GC/time/{PID}/all",
    f"GC/time/{PID}/0",
    f"GC/time/{PID}/1",
    f"GC/time/{PID}/2",
)


@pytest.mark.xfail(
    platform.python_implementation() == "PyPy", reason="Not implemented on PyPy yet", strict=True, raises=AssertionError
)
@pytest.mark.parametrize("top_object_count_limit", (1, 0))
def test_gc_metrics_collection(gc_data_source, top_object_count_limit):
    @override_generic_settings(
        settings,
        {"gc_runtime_metrics.enabled": True, "gc_runtime_metrics.top_object_count_limit": top_object_count_limit},
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


@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="GC Metrics are always disabled on PyPy")
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
    "Memory/Physical/Utilization",
    f"Memory/Physical/{PID}",
    f"Memory/Physical/Utilization/{PID}",
)


@pytest.mark.parametrize("enabled", (True, False))
def test_memory_metrics_collection(memory_data_source, enabled):
    @override_generic_settings(settings, {"memory_runtime_pid_metrics.enabled": enabled})
    def _test():
        metrics_table = set(m[0] for m in (memory_data_source() or ()))
        if enabled:
            for metric in EXPECTED_MEMORY_METRICS:
                assert metric in metrics_table
        else:
            assert EXPECTED_MEMORY_METRICS[0] in metrics_table
            assert EXPECTED_MEMORY_METRICS[1] in metrics_table

    _test()
