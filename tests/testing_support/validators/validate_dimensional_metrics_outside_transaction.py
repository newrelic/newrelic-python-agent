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

import copy

from testing_support.fixtures import catch_background_exceptions
from newrelic.common.object_wrapper import transient_function_wrapper, function_wrapper


def validate_dimensional_metrics_outside_transaction(dimensional_metrics=None):
    dimensional_metrics = dimensional_metrics or []

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_dimensional_metric_called = []
        recorded_metrics = [None]

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_dimensional_metric")
        @catch_background_exceptions
        def _validate_dimensional_metrics_outside_transaction(wrapped, instance, args, kwargs):
            record_dimensional_metric_called.append(True)
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise
            else:
                metrics = instance.dimensional_stats_table.metrics()
                # Record a copy of the metric value so that the values aren't
                # merged in the future
                _metrics = {}
                for k, v in metrics:
                    _metrics[k] = copy.copy(v)
                recorded_metrics[0] = _metrics

            return result

        def _validate(metrics, name, tags, count):
            key = (name, tags)
            # Dimensional metric lookup
            metric_container = metrics.get(name, {})
            metric = metric_container.get(tags)

            def _metrics_table():
                out = [""]
                out.append("Expected: {0}: {1}".format(key, count))
                for metric_key, metric_container in metrics.items():
                    if isinstance(metric_container, dict):
                        for metric_tags, metric_value in metric_container.items():
                            out.append("{0}: {1}".format((metric_key, metric_tags), metric_value[0]))
                    else:
                        out.append("{0}: {1}".format(metric_key, metric_container[0]))
                return "\n".join(out)

            def _metric_details():
                return "metric=%r, count=%r" % (key, metric.call_count)

            if count is not None:
                assert metric is not None, _metrics_table()
                if count == "present":
                    assert metric.call_count > 0, _metric_details()
                else:
                    assert metric.call_count == count, _metric_details()

                assert metric.total_call_time >= 0, (key, metric)
                assert metric.total_exclusive_call_time >= 0, (key, metric)
                assert metric.min_call_time >= 0, (key, metric)
                assert metric.sum_of_squares >= 0, (key, metric)

            else:
                assert metric is None, _metrics_table()

        _new_wrapper = _validate_dimensional_metrics_outside_transaction(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_dimensional_metric_called
        metrics = recorded_metrics[0]

        record_dimensional_metric_called[:] = []
        recorded_metrics[:] = []

        for dimensional_metric, dimensional_tags, count in dimensional_metrics:
            if isinstance(dimensional_tags, dict):
                dimensional_tags = frozenset(dimensional_tags.items())
            _validate(metrics, dimensional_metric, dimensional_tags, count)

        return val

    return _validate_wrapper
