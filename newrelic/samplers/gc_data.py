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
import time
from newrelic.samplers.decorators import data_source_factory
from newrelic.core.stats_engine import CustomMetrics



@data_source_factory(name="Garbage Collector Metrics")
class _GCDataSource(object):
    def __init__(self, settings, environ):
        self.gc_time_metrics = CustomMetrics()
        self.start_time = 0.0

    def record_gc(self, phase, info):
        current_generation = info['generation']

        if phase == 'start':
            self.start_time = time.time()
        elif phase == 'stop':
            total_time = time.time() - self.start_time
            self.gc_time_metrics.record_custom_metric(
                    'GC/time/all', total_time)
            for gen in range(0, 3):
                if gen <= current_generation:
                    self.gc_time_metrics.record_custom_metric(
                        'GC/time/generation/%d' % (gen, ), total_time)


    def start(self):
        if hasattr(gc, 'callbacks'):
            gc.callbacks.append(self.record_gc)


    def stop(self):
        # The callback must be removed before resetting the metrics tables.
        # If it isn't, it's possible to be interrupted by the gc and to have more
        # metrics appear in the table that should be empty.
        if hasattr(gc, 'callbacks') and self.record_gc in gc.callbacks:
            gc.callbacks.remove(self.record_gc)

        self.gc_time_metrics.reset_metric_stats()
        self.start_time = 0.0


    def __call__(self):
        if hasattr(gc, "get_count"):
            counts = gc.get_count()
            yield ("GC/objects/all", {"count": sum(counts)})
            for gen, count in enumerate(counts):
                yield ("GC/objects/generation/%d" % (gen,), {"count": count})

        if hasattr(gc, "get_stats"):
            stats = gc.get_stats()
            if isinstance(stats, list):
                for stat_name in stats[0].keys():
                    count = sum(stat[stat_name] for stat in stats)
                    yield ("GC/stats/%s/all" % (stat_name,), {"count": count})
                    for gen, stat in enumerate(stats):
                        yield (
                            "GC/stats/%s/generation/%d" % (stat_name, gen),
                            {"count": stat[stat_name]},
                        )

        # In order to avoid a concurrency issue with getting interrupted by the
        # garbage collector, we save a reference to the old metrics table, and overwrite
        # self.gc_time_metrics with a new empty table via reset_metric_stats().
        # This guards against losing data points, or having inconsistent data points
        # reported between /all and the totals of /generation/%d metrics.
        gc_time_metrics = self.gc_time_metrics.metrics()
        self.gc_time_metrics.reset_metric_stats()
        
        for metric in gc_time_metrics:
            raw_metric = metric[1]
            yield metric[0], {
                'count': raw_metric.call_count,
                'total': raw_metric.total_call_time,
                'min': raw_metric.min_call_time,
                'max': raw_metric.max_call_time,
                'sum_of_squares': raw_metric.sum_of_squares,
            }


garbage_collector_data_source = _GCDataSource
