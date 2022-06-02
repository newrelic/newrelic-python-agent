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

import pytest
import sys
from testing_support.fixtures import validate_transaction_metrics
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)

from starlette import __version__
starlette_version = tuple(int(x) for x in __version__.split("."))

try:
    from starlette.middleware import Middleware     # Ignore Flake8 Error

    no_middleware = False
except ImportError:
    no_middleware = True

skip_if_no_middleware = pytest.mark.skipif(
    no_middleware, reason="These tests verify middleware functionality"
)


@pytest.fixture(scope="session")
def target_application():
    import _test_bg_tasks

    return _test_bg_tasks.target_application


@pytest.mark.parametrize("route", ["async", "sync"])
def test_simple(target_application, route):
    route_metrics = [("Function/_test_bg_tasks:run_%s_bg_task" % route, 1)]

    @validate_transaction_metrics(
        "_test_bg_tasks:run_%s_bg_task" % route, index=-2, scoped_metrics=route_metrics
    )
    @validate_transaction_metrics(
        "_test_bg_tasks:%s_bg_task" % route, background_task=True
    )
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

    @validate_transaction_metrics(
        "_test_bg_tasks:run_%s_bg_task" % route, index=-2, scoped_metrics=route_metrics
    )
    @validate_transaction_metrics(
        "_test_bg_tasks:%s_bg_task" % route, background_task=True
    )
    @validate_transaction_count(2)
    def _test():
        app = target_application["asgi"]
        response = app.get("/" + route)
        assert response.status == 200

    _test()


@skip_if_no_middleware
@pytest.mark.parametrize("route", ["async", "sync"])
def test_basehttp_style_middleware(target_application, route):
    route_metrics = [("Function/_test_bg_tasks:run_%s_bg_task" % route, 1)]
    old_metrics = [
        ("Function/_test_bg_tasks:%s_bg_task" % route, 1),
        ("Function/_test_bg_tasks:run_%s_bg_task" % route, 1),
    ]

    def _test():
        app = target_application["basehttp"]
        response = app.get("/" + route)
        assert response.status == 200

    if starlette_version >= (0, 20, 1):
        if sys.version_info[:2] > (3, 7):
            _test = validate_transaction_metrics(
                "_test_bg_tasks:run_%s_bg_task" % route, index=-2, scoped_metrics=route_metrics
            )(_test)
            _test = validate_transaction_metrics(
                "_test_bg_tasks:%s_bg_task" % route, background_task=True
            )(_test)
            _test = validate_transaction_count(2)(_test)
        else:   # Python <= 3.7 requires this specific configuration with starlette 0.20.1
            _test = validate_transaction_metrics(
                "_test_bg_tasks:run_%s_bg_task" % route, scoped_metrics=route_metrics
            )(_test)
            _test = validate_transaction_count(1)(_test)
    else:
        _test = validate_transaction_metrics(
            "_test_bg_tasks:run_%s_bg_task" % route, scoped_metrics=old_metrics
        )(_test)
        _test = validate_transaction_count(1)(_test)

    _test()
