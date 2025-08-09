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
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
)
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics

from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_count import validate_transaction_count

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
    "instrumentation.django_middleware.enabled": True,
    "instrumentation.django_middleware.include": ["django.middleware.*", "django.middleware.co*", "django.contrib.messages.middleware:MessageMiddleware"],
    "instrumentation.django_middleware.exclude": ["django.middleware.c*"],
}


scoped_metrics_wildcard_exclude_wildcard_include = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1),
    ("Function/django.middleware.common:CommonMiddleware", 1),  # Specific include overrides wildcard exclude
    ("Function/django.middleware.csrf:CsrfViewMiddleware", None),  # Wildcard exclude
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", 1),
    ("Function/django.middleware.gzip:GZipMiddleware", 1),
    ("Function/middleware:ExceptionTo410Middleware", 1),
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

collector_agent_registration = collector_agent_registration_fixture(
    app_name=f"Python Agent Test (framework_django)", default_settings=_default_settings, scope="module"
)

@pytest.fixture(scope="function")
def application():
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    return AsgiTest(get_asgi_application())


@validate_transaction_count(1)
@validate_transaction_metrics(
    "views:index",
    scoped_metrics=[("Function/views:index", 1)] + scoped_metrics_wildcard_exclude_wildcard_include,
    rollup_metrics=scoped_metrics_wildcard_exclude_wildcard_include + [(f"Python/Framework/Django/{django.get_version()}", 1)]
)
@validate_code_level_metrics("views", "index")
def test_wildcard_exclude_wildcard_include_filter(application):
    response = application.get("/")
    assert response.status == 200
