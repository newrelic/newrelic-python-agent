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

import sys

import pytest
import starlette
from testing_support.fixtures import override_ignore_status_codes

from newrelic.common.object_names import callable_name
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

starlette_version = tuple(int(x) for x in starlette.__version__.split("."))

@pytest.fixture(scope="session")
def target_application():
    import _test_application

    return _test_application.target_application


FRAMEWORK_METRIC = ("Python/Framework/Starlette/%s" % starlette.__version__, 1)

if starlette_version >= (0, 20, 1):
    DEFAULT_MIDDLEWARE_METRICS = [
        ("Function/starlette.middleware.errors:ServerErrorMiddleware.__call__", 1),
        ("Function/starlette.middleware.exceptions:ExceptionMiddleware.__call__", 1),
    ]
else:
    DEFAULT_MIDDLEWARE_METRICS = [
        ("Function/starlette.middleware.errors:ServerErrorMiddleware.__call__", 1),
        ("Function/starlette.exceptions:ExceptionMiddleware.__call__", 1),
    ]

MIDDLEWARE_METRICS = [
    ("Function/_test_application:middleware_factory.<locals>.middleware", 2),
    ("Function/_test_application:middleware_decorator", 1),
] + DEFAULT_MIDDLEWARE_METRICS


@pytest.mark.parametrize("app_name", ("no_error_handler",))
@validate_transaction_metrics(
    "_test_application:index",
    scoped_metrics=MIDDLEWARE_METRICS + [("Function/_test_application:index", 1)],
    rollup_metrics=[FRAMEWORK_METRIC],
)
@validate_code_level_metrics("_test_application", "index")
@validate_code_level_metrics("_test_application.middleware_factory.<locals>", "middleware", count=2)
def test_application_index(target_application, app_name):
    app = target_application[app_name]
    response = app.get("/index")
    assert response.status == 200


@pytest.mark.parametrize("app_name", ("no_error_handler",))
@validate_transaction_metrics(
    "_test_application:non_async",
    scoped_metrics=MIDDLEWARE_METRICS + [("Function/_test_application:non_async", 1)],
    rollup_metrics=[FRAMEWORK_METRIC],
)
@validate_code_level_metrics("_test_application", "non_async")
@validate_code_level_metrics("_test_application.middleware_factory.<locals>", "middleware", count=2)
def test_application_non_async(target_application, app_name):
    app = target_application[app_name]
    response = app.get("/non_async")
    assert response.status == 200

# Starting in Starlette v0.20.1, the ExceptionMiddleware class
# has been moved to the starlette.middleware.exceptions from
# starlette.exceptions
version_tweak_string = ".middleware" if starlette_version >= (0, 20, 1) else ""

DEFAULT_MIDDLEWARE_METRICS = [
    ("Function/starlette.middleware.errors:ServerErrorMiddleware.__call__", 1),
    ("Function/starlette%s.exceptions:ExceptionMiddleware.__call__" % version_tweak_string, 1),
]

middleware_test = (
    ("no_error_handler", "starlette%s.exceptions:ExceptionMiddleware.__call__" % version_tweak_string),
    (
        "non_async_error_handler_no_middleware",
        "starlette%s.exceptions:ExceptionMiddleware.__call__" % version_tweak_string,
    ),
)

@pytest.mark.parametrize(
    "app_name, transaction_name", middleware_test,
)
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
def test_exception_in_middleware(target_application, app_name):
    app = target_application[app_name]

    from starlette import __version__ as version

    starlette_version = tuple(int(v) for v in version.split("."))

    # Starlette >=0.15 and <0.17 raises an exception group instead of reraising the ValueError
    # This only occurs on Python versions >=3.8
    if sys.version_info[0:2] > (3, 7) and starlette_version >= (0, 15, 0) and starlette_version < (0, 17, 0):
        from anyio._backends._asyncio import ExceptionGroup

        exc_type = ExceptionGroup
    else:
        exc_type = ValueError

    @validate_transaction_metrics(
        "_test_application:middleware_factory.<locals>.middleware",
        scoped_metrics=[("Function/_test_application:middleware_factory.<locals>.middleware", 1)],
        rollup_metrics=[FRAMEWORK_METRIC],
    )
    @validate_transaction_errors(errors=[callable_name(exc_type)])
    def _test():
        with pytest.raises(exc_type):  # Later versions of starlette
            app.get("/crash_me_now")

    _test()


@pytest.mark.parametrize(
    "app_name,transaction_name,path,scoped_metrics",
    (
        (
            "non_async_error_handler_no_middleware",
            "_test_application:runtime_error",
            "/runtime_error",
            [],
        ),
        (
            "async_error_handler_no_middleware",
            "_test_application:runtime_error",
            "/runtime_error",
            [("Function/_test_application:async_error_handler", 1)],
        ),
        (
            "no_middleware",
            "_test_application:runtime_error",
            "/runtime_error",
            [
                (
                    "Function/starlette.middleware.errors:ServerErrorMiddleware.error_response",
                    1,
                )
            ],
        ),
        (
            "debug_no_middleware",
            "_test_application:runtime_error",
            "/runtime_error",
            [
                (
                    "Function/starlette.middleware.errors:ServerErrorMiddleware.debug_response",
                    1,
                )
            ],
        ),
        ("no_middleware", "_test_application:CustomRoute", "/raw_runtime_error", []),
    ),
)
@validate_transaction_errors(errors=["builtins:RuntimeError"])
def test_server_error_middleware(target_application, app_name, transaction_name, path, scoped_metrics):
    @validate_transaction_metrics(
        transaction_name,
        scoped_metrics=scoped_metrics + [("Function/_test_application:runtime_error", 1)] + DEFAULT_MIDDLEWARE_METRICS,
        rollup_metrics=[FRAMEWORK_METRIC],
    )
    def _test():
        app = target_application[app_name]
        with pytest.raises(RuntimeError):
            app.get(path)

    _test()


@pytest.mark.parametrize(
    "app_name,transaction_name,path,error",
    (
        (
            "async_error_handler_no_middleware",
            "_test_application:handled_error",
            "/handled_error",
            "_test_application:HandledError",
        ),
        (
            "non_async_error_handler_no_middleware",
            "_test_application:non_async_handled_error",
            "/non_async_handled_error",
            "_test_application:NonAsyncHandledError",
        ),
    ),
)
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


@pytest.mark.parametrize(
    "app_name,transaction_name,path",
    (
        (
            "async_error_handler_no_middleware",
            "_test_application:handled_error",
            "/handled_error",
        ),
        (
            "non_async_error_handler_no_middleware",
            "_test_application:non_async_handled_error",
            "/non_async_handled_error",
        ),
    ),
)
@override_ignore_status_codes(set((500,)))
def test_application_ignored_error(target_application, app_name, transaction_name, path):
    @validate_transaction_errors(errors=[])
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


middleware_test_exception = (
    (
        "no_middleware",
        [("Function/starlette%s.exceptions:ExceptionMiddleware.http_exception" % version_tweak_string, 1)],
    ),
    (
        "teapot_exception_handler_no_middleware",
        [("Function/_test_application:teapot_handler", 1)],
    ),
)

@pytest.mark.parametrize(
    "app_name,scoped_metrics", middleware_test_exception
)
def test_starlette_http_exception(target_application, app_name, scoped_metrics):
    @validate_transaction_errors(errors=["starlette.exceptions:HTTPException"])
    @validate_transaction_metrics(
        "_test_application:teapot",
        scoped_metrics=scoped_metrics + DEFAULT_MIDDLEWARE_METRICS,
        rollup_metrics=[FRAMEWORK_METRIC],
    )
    def _test():
        app = target_application[app_name]
        response = app.get("/418")
        assert response.status == 418

    _test()


@pytest.mark.parametrize("app_name", ("no_middleware",))
@validate_transaction_errors(errors=["builtins:RuntimeError"])
@validate_transaction_metrics("_test_application:CustomRoute", rollup_metrics=[FRAMEWORK_METRIC])
def test_starlette_http_exception_after_response_start(target_application, app_name):
    app = target_application[app_name]
    with pytest.raises(RuntimeError):
        app.get("/raw_http_error")
