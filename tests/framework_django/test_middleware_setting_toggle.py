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

import os

import django
import pytest
from testing_support.fixtures import collector_available_fixture, django_collector_agent_registration_fixture
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

DJANGO_VERSION = tuple(map(int, django.get_version().split(".")[:2]))

if DJANGO_VERSION[0] < 3:
    pytest.skip("support for asgi added in django 3", allow_module_level=True)

# Import this here so it is not run if Django is less than 3.0.
from testing_support.asgi_testing import AsgiTest  # noqa: E402

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_autorum_middleware": True,
}


@pytest.fixture(params=[False, True])
def settings_and_metrics(request):
    collect_middleware = request.param
    middleware_scoped_metrics = [
        ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1 if collect_middleware else None),
        ("Function/django.middleware.common:CommonMiddleware", 1 if collect_middleware else None),
        ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1 if collect_middleware else None),
        ("Function/django.contrib.messages.middleware:MessageMiddleware", 1 if collect_middleware else None),
        ("Function/django.middleware.gzip:GZipMiddleware", 1 if collect_middleware else None),
        ("Function/middleware:ExceptionTo410Middleware", 1 if collect_middleware else None),
        ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
    ]
    _default_settings["instrumentation.django_middleware.enabled"] = collect_middleware
    return _default_settings, middleware_scoped_metrics


@pytest.fixture
def settings_fixture(request, settings_and_metrics):
    _default_settings, _ = settings_and_metrics
    return _default_settings


@pytest.fixture
def middleware_scoped_metrics(request, settings_and_metrics):
    _, middleware_scoped_metrics = settings_and_metrics
    return middleware_scoped_metrics + [("Function/views:index", 1)]


@pytest.fixture
def middleware_rollup_metrics(request, settings_and_metrics):
    _, middleware_scoped_metrics = settings_and_metrics
    return middleware_scoped_metrics + [(f"Python/Framework/Django/{django.get_version()}", 1)]


@pytest.fixture
def application():
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    return AsgiTest(get_asgi_application())


collector_agent_registration = django_collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_django)", scope="function"
)


def test_asgi_middleware_toggled_setting(application, middleware_scoped_metrics, middleware_rollup_metrics):
    @validate_transaction_metrics(
        "views:index", scoped_metrics=middleware_scoped_metrics, rollup_metrics=middleware_rollup_metrics
    )
    @validate_code_level_metrics("views", "index")
    def _test():
        response = application.get("/")
        assert response.status == 200

    _test()
