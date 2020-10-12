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

import starlette
import pytest
from testing_support.fixtures import (
    validate_transaction_metrics,
    validate_transaction_errors,
    capture_transaction_metrics,
    override_ignore_status_codes,
)


FRAMEWORK_METRIC = ("Python/Framework/Starlette/%s" % starlette.__version__, 1)
MIDDLEWARE_METRICS = [
    ("Function/starlette.middleware.errors:ServerErrorMiddleware.__call__", 1),
    ("Function/starlette.exceptions:ExceptionMiddleware.__call__", 1),
    ("Function/_target_application:middleware.<locals>.middleware", 2),
    ("Function/_target_application:middleware_decorator", 1),
]


@validate_transaction_metrics(
    "_target_application:index",
    scoped_metrics=MIDDLEWARE_METRICS + [("Function/_target_application:index", 1)],
    rollup_metrics=[FRAMEWORK_METRIC],
)
def test_application_index(target_application):
    response = target_application.get("/index")
    assert response.status == 200


@validate_transaction_metrics(
    "_target_application:non_async",
    scoped_metrics=MIDDLEWARE_METRICS + [("Function/_target_application:non_async", 1)],
    rollup_metrics=[FRAMEWORK_METRIC],
)
def test_application_non_async(target_application):
    response = target_application.get("/non_async")
    assert response.status == 200


@validate_transaction_errors(errors=["builtins:RuntimeError"])
@validate_transaction_metrics(
    "_target_application:runtime_error",
    scoped_metrics=MIDDLEWARE_METRICS + [("Function/_target_application:runtime_error", 1)],
    rollup_metrics=[FRAMEWORK_METRIC],
)
def test_application_generic_error(target_application):
    # When the generic exception handler is used, the error is reraised
    with pytest.raises(RuntimeError):
        target_application.get("/runtime_error")


@validate_transaction_errors(errors=["_target_application:HandledError"])
@validate_transaction_metrics(
    "_target_application:handled_error",
    scoped_metrics=MIDDLEWARE_METRICS + [("Function/_target_application:handled_error", 1)],
    rollup_metrics=[FRAMEWORK_METRIC],
)
def test_application_handled_error(target_application):
    response = target_application.get("/handled_error")
    assert response.status == 500


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "_target_application:handled_error", rollup_metrics=[FRAMEWORK_METRIC]
)
@override_ignore_status_codes(set((500,)))
def test_application_ignored_error(target_application):
    response = target_application.get("/handled_error")
    assert response.status == 500


def test_application_background_tasks(target_application):
    metrics = []
    expected_metrics = [
        'OtherTransaction/Function/_target_application:bg_task_async',
        'OtherTransaction/Function/_target_application:bg_task_non_async',
        'Function/_target_application:run_bg_task'
    ]

    @capture_transaction_metrics(metrics)
    def _test():
        response = target_application.get("/run_bg_task")
        assert response.status == 200

    _test()

    metric_names = {metric[0] for metric in metrics}
    for metric in expected_metrics:
        assert metric in metric_names