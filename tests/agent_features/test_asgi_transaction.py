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

import asyncio
import logging
import pytest
from testing_support.sample_asgi_applications import (
    simple_app_v2_raw,
    simple_app_v3_raw,
    simple_app_v2,
    simple_app_v3,
    AppWithDescriptor,
    simple_app_v2_init_exc,
)
from testing_support.fixtures import (
    validate_transaction_metrics,
    override_application_settings,
    function_not_called,
    validate_transaction_errors,
)
from newrelic.api.asgi_application import asgi_application, ASGIApplicationWrapper
from testing_support.asgi_testing import AsgiTest

# Setup test apps from sample_asgi_applications.py
simple_app_v2_original = AsgiTest(simple_app_v2_raw)
simple_app_v3_original = AsgiTest(simple_app_v3_raw)

simple_app_v3_wrapped = AsgiTest(simple_app_v3)
simple_app_v2_wrapped = AsgiTest(simple_app_v2)
simple_app_v2_init_exc = AsgiTest(simple_app_v2_init_exc)


# Test naming scheme logic and ASGIApplicationWrapper for a single callable
@pytest.mark.parametrize("naming_scheme", (None, "component", "framework"))
def test_single_callable_naming_scheme(naming_scheme):

    if naming_scheme in ("component", "framework"):
        expected_name = "testing_support.sample_asgi_applications:simple_app_v3_raw"
        expected_group = "Function"
    else:
        expected_name = ""
        expected_group = "Uri"

    @validate_transaction_metrics(name=expected_name, group=expected_group)
    @override_application_settings({"transaction_name.naming_scheme": naming_scheme})
    def _test():
        response = simple_app_v3_wrapped.make_request("GET", "/")
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b""

    _test()


# Test the default naming scheme logic and ASGIApplicationWrapper for a double callable
@validate_transaction_metrics(name="", group="Uri")
def test_double_callable_default_naming_scheme():
    response = simple_app_v2_wrapped.make_request("GET", "/")
    assert response.status == 200
    assert response.headers == {}
    assert response.body == b""


# No harm test on single callable asgi app with agent disabled to ensure proper response
def test_single_callable_raw():
    response = simple_app_v3_original.make_request("GET", "/")
    assert response.status == 200
    assert response.headers == {}
    assert response.body == b""


# No harm test on double callable asgi app with agent disabled to ensure proper response
def test_double_callable_raw():
    response = simple_app_v2_original.make_request("GET", "/")
    assert response.status == 200
    assert response.headers == {}
    assert response.body == b""


# Test asgi_application decorator with parameters passed in on a single callable
@pytest.mark.parametrize(
    "name, group", ((None, "group"), ("name", "group"), ("", "group"))
)
def test_asgi_application_decorator_single_callable(name, group):
    if name:
        expected_name = name
        expected_group = group
    else:
        expected_name = ""
        expected_group = "Uri"

    @validate_transaction_metrics(name=expected_name, group=expected_group)
    def _test():
        asgi_decorator = asgi_application(name=name, group=group)
        decorated_application = asgi_decorator(simple_app_v3_raw)
        application = AsgiTest(decorated_application)
        response = application.make_request("GET", "/")
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b""

    _test()


# Test asgi_application decorator using default values on a double callable
@validate_transaction_metrics(name="", group="Uri")
def test_asgi_application_decorator_no_params_double_callable():
    asgi_decorator = asgi_application()
    decorated_application = asgi_decorator(simple_app_v2_raw)
    application = AsgiTest(decorated_application)
    response = application.make_request("GET", "/")
    assert response.status == 200
    assert response.headers == {}
    assert response.body == b""


# Test for presence of framework info based on whether framework is specified
@validate_transaction_metrics(
    name="test", custom_metrics=[("Python/Framework/framework/v1", 1)]
)
def test_framework_metrics():
    asgi_decorator = asgi_application(name="test", framework=("framework", "v1"))
    decorated_application = asgi_decorator(simple_app_v2_raw)
    application = AsgiTest(decorated_application)
    application.make_request("GET", "/")


@pytest.mark.parametrize("method", ("method", "cls", "static"))
@validate_transaction_metrics(name="", group="Uri")
def test_app_with_descriptor(method):
    application = AsgiTest(getattr(AppWithDescriptor(), method))
    response = application.make_request("GET", "/")
    assert response.status == 200
    assert response.headers == {}
    assert response.body == b""


# Verify that errors are not generated when using multiple wrappers
def test_multiple_calls_to_asgi_wrapper(caplog):
    app = ASGIApplicationWrapper(simple_app_v3)
    app = AsgiTest(app)

    with caplog.at_level(logging.ERROR, logger="newrelic"):
        response = app.make_request("GET", "/")

    assert response.status == 200
    assert not caplog.records


def test_non_http_scope_v3():
    async def _test():
        await simple_app_v3({"type": "cookies"}, None, None)

    loop = asyncio.get_event_loop()
    with pytest.raises(ValueError):
        loop.run_until_complete(_test())


def test_non_http_scope_v2():
    async def _test():
        call_me = simple_app_v2({"type": "cookies"})
        await call_me(None, None)

    loop = asyncio.get_event_loop()
    with pytest.raises(ValueError):
        loop.run_until_complete(_test())


@pytest.mark.parametrize(
    "app", (simple_app_v3_wrapped, simple_app_v2_wrapped, simple_app_v2_init_exc)
)
@validate_transaction_errors(errors=["builtins:ValueError"])
def test_exception_capture(app):
    with pytest.raises(ValueError):
        app.make_request("GET", "/exc")
