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

# from importlib import reload
import os

import django
import pytest
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture
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
    "feature_flag": {"django.instrumentation.inclusion-tags.r1"},
    "instrumentation.django_middleware.enabled": False,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_django, middleware disabled)", default_settings=_default_settings, scope="function"
)


@pytest.fixture(scope="function")
def application():
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    return AsgiTest(get_asgi_application())


disabled_middleware_scoped_metrics = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", None),
    ("Function/django.middleware.common:CommonMiddleware", None),
    ("Function/django.middleware.csrf:CsrfViewMiddleware", None),
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", None),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", None),
    ("Function/django.middleware.gzip:GZipMiddleware", None),
    ("Function/middleware:ExceptionTo410Middleware", None),
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

disabled_middleware_rollup_metrics = disabled_middleware_scoped_metrics + [(f"Python/Framework/Django/{django.get_version()}", 1)]


@validate_transaction_metrics(
    "views:index", scoped_metrics=[("Function/views:index", 1)] + disabled_middleware_scoped_metrics, rollup_metrics=disabled_middleware_rollup_metrics
)
@validate_code_level_metrics("views", "index")
def test_asgi_middleware_disabled(application):
    response = application.get("/")
    assert response.status == 200
