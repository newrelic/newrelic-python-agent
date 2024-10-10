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

from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_custom_metrics_outside_transaction import (
    validate_custom_metrics_outside_transaction,
)

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.transaction import (
    current_transaction,
    record_custom_metric,
    record_custom_metrics,
)


# Testing record_custom_metric
@reset_core_stats_engine()
@background_task()
def test_custom_metric_inside_transaction():
    transaction = current_transaction()
    record_custom_metric("CustomMetric/InsideTransaction/Count", 1)
    for metric in transaction._custom_metrics.metrics():
        assert metric == ("CustomMetric/InsideTransaction/Count", [1, 1, 1, 1, 1, 1])


@reset_core_stats_engine()
@validate_custom_metrics_outside_transaction([("CustomMetric/OutsideTransaction/Count", 1)])
@background_task()
def test_custom_metric_outside_transaction_with_app():
    app = application()
    record_custom_metric("CustomMetric/OutsideTransaction/Count", 1, application=app)


# Testing record_custom_metricS
@reset_core_stats_engine()
@background_task()
def test_custom_metrics_inside_transaction():
    transaction = current_transaction()
    record_custom_metrics([("CustomMetrics/InsideTransaction/Count", 1)])
    for metric in transaction._custom_metrics.metrics():
        assert metric == ("CustomMetrics/InsideTransaction/Count", [1, 1, 1, 1, 1, 1])


@reset_core_stats_engine()
@validate_custom_metrics_outside_transaction([("CustomMetrics/OutsideTransaction/Count", 1)])
@background_task()
def test_custom_metrics_outside_transaction_with_app():
    app = application()
    record_custom_metrics([("CustomMetrics/OutsideTransaction/Count", 1)], application=app)
