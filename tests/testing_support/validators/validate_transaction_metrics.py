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

def validate_transaction_metrics(
    name,
    group="Function",
    background_task=False,
    scoped_metrics=None,
    rollup_metrics=None,
    custom_metrics=None,
    index=-1,
):
    scoped_metrics = scoped_metrics or []
    rollup_metrics = rollup_metrics or []
    custom_metrics = custom_metrics or []

    if background_task:
        unscoped_metrics = [
            "OtherTransaction/all",
            "OtherTransaction/%s/%s" % (group, name),
            "OtherTransactionTotalTime",
            "OtherTransactionTotalTime/%s/%s" % (group, name),
        ]
        transaction_scope_name = "OtherTransaction/%s/%s" % (group, name)
    else:
        unscoped_metrics = [
            "WebTransaction",
            "WebTransaction/%s/%s" % (group, name),
            "WebTransactionTotalTime",
            "WebTransactionTotalTime/%s/%s" % (group, name),
            "HttpDispatcher",
        ]
        transaction_scope_name = "WebTransaction/%s/%s" % (group, name)

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_transaction_called = []
        recorded_metrics = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        @catch_background_exceptions
        def _validate_transaction_metrics(wrapped, instance, args, kwargs):
            record_transaction_called.append(True)
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

        def _validate(metrics, name, scope, count):
            key = (name, scope)
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
        assert record_transaction_called
        metrics = recorded_metrics[index]

        record_transaction_called[:] = []
        recorded_metrics[:] = []

        for unscoped_metric in unscoped_metrics:
            _validate(metrics, unscoped_metric, "", 1)

        for scoped_name, scoped_count in scoped_metrics:
            _validate(metrics, scoped_name, transaction_scope_name, scoped_count)

        for rollup_name, rollup_count in rollup_metrics:
            _validate(metrics, rollup_name, "", rollup_count)

        for custom_name, custom_count in custom_metrics:
            _validate(metrics, custom_name, "", custom_count)

        custom_metric_names = {name for name, _ in custom_metrics}
        for name, _ in metrics:
            if name not in custom_metric_names:
                assert not name.startswith("Supportability/api/"), name

        return val

    return _validate_wrapper