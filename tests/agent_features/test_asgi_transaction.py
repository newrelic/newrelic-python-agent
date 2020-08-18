import pytest
from testing_support.sample_asgi_applications import simple_app_v2_raw, simple_app_v3_raw, simple_app_v2, simple_app_v3
from testing_support.fixtures import validate_transaction_metrics, override_application_settings, function_not_called
from newrelic.api.asgi_application import asgi_application
from testing_support.asgi_testing import AsgiTest

#Setup test apps from sample_asgi_applications.py
simple_app_v2_original = AsgiTest(simple_app_v2_raw)
simple_app_v3_original = AsgiTest(simple_app_v3_raw)

simple_app_v3_wrapped = AsgiTest(simple_app_v3)
simple_app_v2_wrapped = AsgiTest(simple_app_v2)


#Test naming scheme logic and ASGIApplicationWrapper for a single callable
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


#Test the default naming scheme logic and ASGIApplicationWrapper for a double callable
@validate_transaction_metrics(name="", group="Uri")
def test_double_callable_default_naming_scheme():

    def _test():
        response = simple_app_v2_wrapped.make_request("GET", "/")
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b""

    _test()


#No harm test on single callable asgi app with agent disabled to ensure proper response
def test_single_callable_raw():

    def _test():
        response = simple_app_v3_original.make_request("GET", "/")
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b""

    _test()


#No harm test on double callable asgi app with agent disabled to ensure proper response
def test_double_callable_raw():

    def _test():
        response = simple_app_v3_original.make_request("GET", "/")
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b""

    _test()


#Test asgi_application decorator with parameters passed in on a single callable
@pytest.mark.parametrize("group", (None, "group", ""))
@pytest.mark.parametrize("framework", (None, "function", ""))
def test_asgi_application_decorator_single_callable(group, framework):

    @validate_transaction_metrics(name="", group="Uri")
    def _test():
        asgi_decorator = asgi_application(name="", group=group, framework=framework)
        decorated_application = asgi_decorator(simple_app_v3_raw)
        application = AsgiTest(decorated_application)
        response = application.make_request("GET", "/")
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b""

    _test()


#Test asgi_application decorator using default values on a double callable
def test_asgi_application_decorator_no_params_double_callable():

    @validate_transaction_metrics(name="", group="Uri")
    def _test():
        asgi_decorator = asgi_application()
        decorated_application = asgi_decorator(simple_app_v2_raw)
        application = AsgiTest(decorated_application)
        response = application.make_request("GET", "/")
        assert response.status == 200
        assert response.headers == {}
        assert response.body == b""

    _test()
