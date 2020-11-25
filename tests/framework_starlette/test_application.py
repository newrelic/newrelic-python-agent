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
DEFAULT_MIDDLEWARE_METRICS = [
    ("Function/starlette.middleware.errors:ServerErrorMiddleware.__call__", 1),
    ("Function/starlette.exceptions:ExceptionMiddleware.__call__", 1),
]
MIDDLEWARE_METRICS = [
    ("Function/_target_application:middleware_factory.<locals>.middleware", 2),
    ("Function/_target_application:middleware_decorator", 1),
] + DEFAULT_MIDDLEWARE_METRICS


@pytest.mark.parametrize("app_name", ("no_error_handler",))
@validate_transaction_metrics(
    "_target_application:index",
    scoped_metrics=MIDDLEWARE_METRICS + [("Function/_target_application:index", 1)],
    rollup_metrics=[FRAMEWORK_METRIC],
)
def test_application_index(target_application, app_name):
    app = target_application[app_name]
    response = app.get("/index")
    assert response.status == 200


@pytest.mark.parametrize("app_name", ("no_error_handler",))
@validate_transaction_metrics(
    "_target_application:non_async",
    scoped_metrics=MIDDLEWARE_METRICS + [("Function/_target_application:non_async", 1)],
    rollup_metrics=[FRAMEWORK_METRIC],
)
def test_application_non_async(target_application, app_name):
    app = target_application[app_name]
    response = app.get("/non_async")
    assert response.status == 200


@pytest.mark.parametrize("app_name, transaction_name", (
        ("no_error_handler", "starlette.exceptions:ExceptionMiddleware.__call__"),
        ("non_async_error_handler_no_middleware", "starlette.exceptions:ExceptionMiddleware.__call__"),
    ))
def test_application_nonexistent_route(target_application, app_name, transaction_name):
    @validate_transaction_metrics(
        transaction_name,
        scoped_metrics=[("Function/" + transaction_name, 1)],
        rollup_metrics=[FRAMEWORK_METRIC],
    )
    def _test():
        app = target_application[app_name]
        response = app.get("/nonexistent_route")
        assert response.status == 404
    
    _test()


@pytest.mark.parametrize("app_name", ("no_error_handler",))    
@validate_transaction_metrics(
    "_target_application:middleware_factory.<locals>.middleware",
    scoped_metrics=[("Function/_target_application:middleware_factory.<locals>.middleware", 1)],
    rollup_metrics=[FRAMEWORK_METRIC],
)
def test_exception_in_middleware(target_application, app_name):
    app = target_application[app_name]
    with pytest.raises(ValueError):
        app.get("/crash_me_now")


@pytest.mark.parametrize("app_name,transaction_name,path,scoped_metrics", (
    ("non_async_error_handler_no_middleware", "_target_application:runtime_error", "/runtime_error", []),
    ("async_error_handler_no_middleware", "_target_application:runtime_error", "/runtime_error", [("Function/_target_application:async_error_handler", 1)]),
    ("no_middleware", "_target_application:runtime_error", "/runtime_error", [("Function/starlette.middleware.errors:ServerErrorMiddleware.error_response", 1)]),
    ("debug_no_middleware", "_target_application:runtime_error", "/runtime_error", [("Function/starlette.middleware.errors:ServerErrorMiddleware.debug_response", 1)]),
    ("no_middleware", "_target_application:CustomRoute", "/raw_runtime_error", []),
))
@validate_transaction_errors(errors=["builtins:RuntimeError"])
def test_server_error_middleware(target_application, app_name, transaction_name, path, scoped_metrics):
    @validate_transaction_metrics(
        transaction_name,
        scoped_metrics=scoped_metrics+[("Function/_target_application:runtime_error", 1)]+DEFAULT_MIDDLEWARE_METRICS,
        rollup_metrics=[FRAMEWORK_METRIC],
    )
    def _test():
        app = target_application[app_name]
        with pytest.raises(RuntimeError):
            app.get(path)

    _test()


@pytest.mark.parametrize("app_name,transaction_name,path,error", (
    ("async_error_handler_no_middleware", "_target_application:handled_error", "/handled_error", "_target_application:HandledError"),
    ("non_async_error_handler_no_middleware", "_target_application:non_async_handled_error", "/non_async_handled_error", "_target_application:NonAsyncHandledError")
))
def test_application_handled_error(target_application, app_name, transaction_name, path, error):
    @validate_transaction_errors(errors=[error])
    @validate_transaction_metrics(
        transaction_name,
        scoped_metrics=[("Function/" + transaction_name, 1)],
        rollup_metrics=[FRAMEWORK_METRIC],
    )
    def _test():
        app = target_application[app_name]
        response = app.get(path)
        assert response.status == 500

    _test()


@pytest.mark.parametrize("app_name,transaction_name,path", (
    ("async_error_handler_no_middleware", "_target_application:handled_error", "/handled_error"),
    ("non_async_error_handler_no_middleware", "_target_application:non_async_handled_error", "/non_async_handled_error")
))
@override_ignore_status_codes(set((500,)))
def test_application_ignored_error(target_application, app_name, transaction_name, path):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        transaction_name,
        scoped_metrics=[("Function/" + transaction_name, 1)],
        rollup_metrics=[FRAMEWORK_METRIC]
    )
    def _test():
        app = target_application[app_name]
        response = app.get(path)
        assert response.status == 500
    _test()



@pytest.mark.parametrize("app_name,scoped_metrics", (
    ("no_middleware", [("Function/starlette.exceptions:ExceptionMiddleware.http_exception", 1)]),
    ("teapot_exception_handler_no_middleware", [("Function/_target_application:teapot_handler", 1)])
))
def test_starlette_http_exception(target_application, app_name, scoped_metrics):
    @validate_transaction_errors(errors=["starlette.exceptions:HTTPException"])
    @validate_transaction_metrics(
        "_target_application:teapot",
        scoped_metrics=scoped_metrics+DEFAULT_MIDDLEWARE_METRICS,
        rollup_metrics=[FRAMEWORK_METRIC]
    )
    def _test():
        app = target_application[app_name]
        response = app.get("/418")
        assert response.status == 418

    _test()


@pytest.mark.parametrize("app_name", ("no_middleware",))
@validate_transaction_errors(errors=["builtins:RuntimeError"])
@validate_transaction_metrics(
    "_target_application:CustomRoute", rollup_metrics=[FRAMEWORK_METRIC]
)
def test_starlette_http_exception_after_response_start(target_application, app_name):
    app = target_application[app_name]
    with pytest.raises(RuntimeError):
        app.get("/raw_http_error")


@pytest.mark.parametrize("app_name", ("no_error_handler",))
def test_application_background_tasks(target_application, app_name):
    app = target_application[app_name]
    metrics = []
    expected_metrics = [
        'OtherTransaction/Function/_target_application:bg_task_async',
        'OtherTransaction/Function/_target_application:bg_task_non_async',
        'Function/_target_application:run_bg_task'
    ]

    @capture_transaction_metrics(metrics)
    def _test():
        response = app.get("/run_bg_task")
        assert response.status == 200

    _test()

    metric_names = {metric[0] for metric in metrics}
    for metric in expected_metrics:
        assert metric in metric_names


