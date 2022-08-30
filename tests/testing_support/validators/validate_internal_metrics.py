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

from newrelic.common.object_wrapper import (
    function_wrapper,
    transient_function_wrapper,
)
from newrelic.core.stats_engine import CustomMetrics
from newrelic.core.internal_metrics import InternalTraceContext


def validate_internal_metrics(metrics=None):
    metrics = metrics or []

    def no_op(wrapped, instance, args, kwargs):
        pass

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        # Apply no-op wrappers to prevent new internal trace contexts from being started, preventing capture
        wrapped = transient_function_wrapper("newrelic.core.internal_metrics", "InternalTraceContext.__enter__")(no_op)(wrapped)
        wrapped = transient_function_wrapper("newrelic.core.internal_metrics", "InternalTraceContext.__exit__")(no_op)(wrapped)

        captured_metrics = CustomMetrics()
        with InternalTraceContext(captured_metrics):
            result = wrapped(*args, **kwargs)
        captured_metrics = dict(captured_metrics.metrics())

        def _validate(name, count):
            metric = captured_metrics.get(name)

            def _metrics_table():
                return "metric=%r, metrics=%r" % (name, captured_metrics)

            def _metric_details():
                return "metric=%r, count=%r" % (name, metric.call_count)

            if count is not None and count > 0:
                assert metric is not None, _metrics_table()
                if count == "present":
                    assert metric.call_count > 0, _metric_details()
                else:
                    assert metric.call_count == count, _metric_details()

            else:
                assert metric is None, _metrics_table()

        for metric, count in metrics:
            _validate(metric, count)

        return result

    return _validate_wrapper