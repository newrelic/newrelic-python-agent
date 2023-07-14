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
from starlette import __version__
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

starlette_version = tuple(int(x) for x in __version__.split("."))

try:
    from starlette.middleware import Middleware  # noqa: F401

    no_middleware = False
except ImportError:
    no_middleware = True

skip_if_no_middleware = pytest.mark.skipif(no_middleware, reason="These tests verify middleware functionality")


@pytest.fixture(scope="session")
def target_application():
    import _test_bg_tasks

    return _test_bg_tasks.target_application


@pytest.mark.parametrize("route", ["async", "sync"])
def test_simple(target_application, route):
    route_metrics = [("Function/_test_bg_tasks:run_%s_bg_task" % route, 1)]

    @validate_transaction_metrics("_test_bg_tasks:run_%s_bg_task" % route, index=-2, scoped_metrics=route_metrics)
    @validate_transaction_metrics("_test_bg_tasks:%s_bg_task" % route, background_task=True)
    @validate_transaction_count(2)
    def _test():
        app = target_application["none"]
        response = app.get("/" + route)
        assert response.status == 200

    _test()


@skip_if_no_middleware
@pytest.mark.parametrize("route", ["async", "sync"])
def test_asgi_style_middleware(target_application, route):
    route_metrics = [("Function/_test_bg_tasks:run_%s_bg_task" % route, 1)]

    @validate_transaction_metrics("_test_bg_tasks:run_%s_bg_task" % route, index=-2, scoped_metrics=route_metrics)
    @validate_transaction_metrics("_test_bg_tasks:%s_bg_task" % route, background_task=True)
    @validate_transaction_count(2)
    def _test():
        app = target_application["asgi"]
        response = app.get("/" + route)
        assert response.status == 200

    _test()


@skip_if_no_middleware
@pytest.mark.parametrize("route", ["async", "sync"])
def test_basehttp_style_middleware(target_application, route):
    route_metric = ("Function/_test_bg_tasks:run_%s_bg_task" % route, 1)
    # A function trace metric that appears only when the bug below is present, causing background tasks to be
    # completed inside web transactions, requiring a function trace to be used for timing
    # instead of a background task transaction. Should not be present at all when bug is fixed.
    bg_task_metric = ("Function/_test_bg_tasks:%s_bg_task" % route, 1)

    def _test():
        app = target_application["basehttp"]
        response = app.get("/" + route)
        assert response.status == 200

    # The bug was fixed in version 0.21.0 but re-occured in 0.23.1.
    # The bug was also not present on 0.20.1 to 0.23.1 if using Python3.7.
    # The bug was fixed again in version 0.29.0
    BUG_COMPLETELY_FIXED = any(
        (
            (0, 21, 0) <= starlette_version < (0, 23, 1),
            (0, 20, 1) <= starlette_version < (0, 23, 1) and sys.version_info[:2] > (3, 7),
            starlette_version >= (0, 29, 0),
        )
    )
    BUG_PARTIALLY_FIXED = any(
        (
            (0, 20, 1) <= starlette_version < (0, 21, 0),
            (0, 23, 1) <= starlette_version < (0, 29, 0),
        )
    )
    if BUG_COMPLETELY_FIXED:
        # Assert both web transaction and background task transactions are present.
        _test = validate_transaction_metrics(
            "_test_bg_tasks:run_%s_bg_task" % route, index=-2, scoped_metrics=[route_metric]
        )(_test)
        _test = validate_transaction_metrics("_test_bg_tasks:%s_bg_task" % route, background_task=True)(_test)
        _test = validate_transaction_count(2)(_test)
    elif BUG_PARTIALLY_FIXED:
        # The background task no longer blocks the completion of the web request/web transaction.
        # However, the BaseHTTPMiddleware causes the task to be cancelled when the web request disconnects, so there are no
        # longer function traces or background task transactions.
        # In version 0.23.1, the check to see if more_body exists is removed, reverting behavior to this model
        _test = validate_transaction_metrics("_test_bg_tasks:run_%s_bg_task" % route, scoped_metrics=[route_metric])(
            _test
        )
        _test = validate_transaction_count(1)(_test)
    else:
        # The BaseHTTPMiddleware causes the background task to execute within the web request
        # with the web transaction still active.
        _test = validate_transaction_metrics(
            "_test_bg_tasks:run_%s_bg_task" % route, scoped_metrics=[route_metric, bg_task_metric]
        )(_test)
        _test = validate_transaction_count(1)(_test)

    _test()
