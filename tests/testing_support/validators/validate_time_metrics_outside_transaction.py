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

from newrelic.common.object_wrapper import (
    function_wrapper,
    transient_function_wrapper,
)
from testing_support.fixtures import catch_background_exceptions

def validate_time_metrics_outside_transaction(time_metrics=None, index=-1):
    time_metrics = time_metrics or []

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_time_metric_called = []
        recorded_metrics = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_time_metric")
        @catch_background_exceptions
        def _validate_transaction_metrics(wrapped, instance, args, kwargs):
            record_time_metric_called.append(True)
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise
            else:
                metrics = instance.stats_table
                # Record a copy of the metric value so that the values aren't
                # merged in the future
                _metrics = {}
                for k, v in metrics.items():
                    _metrics[k] = copy.copy(v)
                recorded_metrics.append(_metrics)

            return result

        def _validate(metrics, name, count):
            key = (name, "")
            metric = metrics.get(key)

            def _metrics_table():
                out = [""]
                out.append("Expected: {0}: {1}".format(key, count))
                for metric_key, metric_value in metrics.items():
                    out.append("{0}: {1}".format(metric_key, metric_value[0]))
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

        _new_wrapper = _validate_transaction_metrics(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_time_metric_called
        metrics = recorded_metrics[index]

        record_time_metric_called[:] = []
        recorded_metrics[:] = []

        for time_metric, count in time_metrics:
            _validate(metrics, time_metric, count)

        return val

    return _validate_wrapper
