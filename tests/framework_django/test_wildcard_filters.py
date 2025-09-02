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
from testing_support.validators.validate_transaction_count import validate_transaction_count
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
    "instrumentation.middleware.django.enabled": True,
}

# Shows more specific include takes priority over wildcard exclude
wildcard_exclude_specific_include_settings = (
    ["django.middleware.*", "django.contrib.messages.middleware:MessageMiddleware"],
    ["django.middleware.csrf:CsrfViewMiddleware"],
)

scoped_metrics_wildcard_exclude_specific_include = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1),
    ("Function/django.middleware.common:CommonMiddleware", None),  # Wildcard exclude
    ("Function/django.middleware.csrf:CsrfViewMiddleware", 1),  # Specific include overrides wildcard exclude
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", None),  # Specific exclude
    ("Function/django.middleware.gzip:GZipMiddleware", None),  # Wildcard exclude
    ("Function/middleware:ExceptionTo410Middleware", 1),
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

# This shows more specific middleware name takes precedence over less specific name.
# Examples:
#   1. "django.middleware.csrf:CsrfViewMiddleware" is excluded because
#       exclude: "django.middleware.c*" is more specific than
#       include: "django.middleware.*"
#   2. "django.middleware.common:CommonMiddleware" is included because
#       exclude: "django.middleware.c*" is less specific than
#       include: "django.middleware.co*"
#   3. Using "django.middleware.common:CommonMiddleware",
#       "django.middleware.*" found in include acts as a no-op because
#       "django.middleware.co*" (also in include list) is more specific.
#       This shows that the first matching wildcard statement within the
#       include list is not the only one evaluated with respect to the
#       middleware name being filtered
wildcard_exclude_wildcard_include_settings = (
    ["django.middleware.c*"],
    ["django.middleware.*", "django.middleware.co*", "django.contrib.messages.middleware:MessageMiddleware"],
)

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

# Shows explicit exclude takes priority over explicit include
specific_exclude_specific_include_settings = (
    ["django.contrib.sessions.middleware:SessionMiddleware", "django.contrib.auth.middleware:AuthenticationMiddleware"],
    ["django.contrib.auth.middleware:AuthenticationMiddleware"],
)

scoped_metrics_specific_exclude_specific_include_settings = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", None),  # Explicit exclude
    ("Function/django.middleware.common:CommonMiddleware", 1),
    ("Function/django.middleware.csrf:CsrfViewMiddleware", 1),
    (
        "Function/django.contrib.auth.middleware:AuthenticationMiddleware",
        None,
    ),  # Explicit exclude overrides explicit include
    ("Function/django.contrib.messages.middleware:MessageMiddleware", 1),
    ("Function/django.middleware.gzip:GZipMiddleware", 1),
    ("Function/middleware:ExceptionTo410Middleware", 1),
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

# Shows explicit exclude behavior with no include
specific_exclude_no_include_settings = (
    ["django.contrib.sessions.middleware:SessionMiddleware", "django.contrib.auth.middleware:AuthenticationMiddleware"],
    [],
)

scoped_metrics_specific_exclude_no_include_settings = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", None),  # Explicit exclude
    ("Function/django.middleware.common:CommonMiddleware", 1),
    ("Function/django.middleware.csrf:CsrfViewMiddleware", 1),
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", None),  # Explicit exclude
    ("Function/django.contrib.messages.middleware:MessageMiddleware", 1),
    ("Function/django.middleware.gzip:GZipMiddleware", 1),
    ("Function/middleware:ExceptionTo410Middleware", 1),
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

# Shows explicit include behavior with no exclude (All middleware will be included)
no_exclude_specific_include_settings = (
    [],
    ["django.contrib.sessions.middleware:SessionMiddleware", "django.contrib.auth.middleware:AuthenticationMiddleware"],
)

scoped_metrics_no_exclude_specific_include_settings = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1),
    ("Function/django.middleware.common:CommonMiddleware", 1),
    ("Function/django.middleware.csrf:CsrfViewMiddleware", 1),
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", 1),
    ("Function/django.middleware.gzip:GZipMiddleware", 1),
    ("Function/middleware:ExceptionTo410Middleware", 1),
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

# Shows the following:
#   1. logic for dot notation for middleware works correctly by using a case where # of dots == 0
#   2. more specific include overrides wildcard exclude
no_dots_wildcard_exclude_specific_include_settings = (
    ["middleware:ExceptionTo410Middle*"],
    ["middleware:ExceptionTo410Middleware"],
)

scoped_metrics_no_dots_wildcard_exclude_specific_include_settings = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1),
    ("Function/django.middleware.common:CommonMiddleware", 1),
    ("Function/django.middleware.csrf:CsrfViewMiddleware", 1),
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", 1),
    ("Function/django.middleware.gzip:GZipMiddleware", 1),
    ("Function/middleware:ExceptionTo410Middleware", 1),  # More specific include overrides wildcard exclude
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

# Shows the following:
#   1. logic for dot notation for middleware works correctly with two wildcards
#   2. more specific exclude takes precedence over include
more_dots_wildcard_exclude_wildcard_include_settings = (
    ["django.middleware.common:CommonMiddle*"],
    ["django.middleware*"],
)

scoped_metrics_more_dots_wildcard_exclude_wildcard_include_settings = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1),
    ("Function/django.middleware.common:CommonMiddleware", None),  # More specific exclude overrides wildcard include
    ("Function/django.middleware.csrf:CsrfViewMiddleware", 1),
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", 1),
    ("Function/django.middleware.gzip:GZipMiddleware", 1),
    ("Function/middleware:ExceptionTo410Middleware", 1),
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

# Shows the following:
#   1. logic for dot notation for middleware works correctly with two wildcards
#   2. more specific include takes precedence over exclude
fewer_dots_wildcard_exclude_wildcard_include_settings = (
    ["django.middleware*"],
    ["django.middleware.common:CommonMiddle*"],
)

scoped_metrics_fewer_dots_wildcard_exclude_wildcard_include_settings = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1),
    ("Function/django.middleware.common:CommonMiddleware", 1),  # More specific include overrides wildcard exclude
    ("Function/django.middleware.csrf:CsrfViewMiddleware", None),
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", 1),
    ("Function/django.middleware.gzip:GZipMiddleware", None),
    ("Function/middleware:ExceptionTo410Middleware", 1),
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

# A case where
#   1. dots in middleware name only in exclude
#   2. explicit middleware name with dot notation in exclude with wildcard middleware name with no dot notation in include
specific_dots_exclude_wildcard_no_dots_include_settings = (
    ["django.contrib.messages.middleware:MessageMiddleware"],
    ["middleware*"],
)

scoped_metrics_specific_dots_exclude_wildcard_no_dots_include_settings = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1),
    ("Function/django.middleware.common:CommonMiddleware", 1),
    ("Function/django.middleware.csrf:CsrfViewMiddleware", 1),
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", None),  # Explicit exclude
    ("Function/django.middleware.gzip:GZipMiddleware", 1),
    ("Function/middleware:ExceptionTo410Middleware", 1),
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

# A case where
#   1. dots in middleware name only in include
#   2. explicit middleware name with dot notation in include with wildcard middleware name with no dot notation in exclude
no_dots_exclude_specific_dots_include_settings = (
    ["middleware*"],
    ["django.contrib.messages.middleware:MessageMiddleware"],
)

scoped_metrics_no_dots_exclude_specific_dots_include_settings = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1),
    ("Function/django.middleware.common:CommonMiddleware", 1),
    ("Function/django.middleware.csrf:CsrfViewMiddleware", 1),
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", 1),
    ("Function/django.middleware.gzip:GZipMiddleware", 1),
    ("Function/middleware:ExceptionTo410Middleware", None),  # Explicit exclude
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]

# Shows the following:
#   1. case sensitivity
#       a. exclude: "DJANGO.CONTRIB.*", "DjAnGo.MiDdLeWaRe.C*"
#       b. include: "django.URLS*"
#   2. incomplete names
#       a. exclude: "middleware"
#       b. include: "gzip"
case_sensitive_and_incomplete_names_settings = (
    ["DJANGO.CONTRIB.*", "django.middleware*", "middleware", "DJANGO*"],
    ["django.CONTRIB.sessions*", "gzip"],
)

scoped_metrics_case_sensitive_and_incomplete_names_settings = [
    ("Function/django.contrib.sessions.middleware:SessionMiddleware", 1),
    ("Function/django.middleware.common:CommonMiddleware", None),  # Explicit exclude
    ("Function/django.middleware.csrf:CsrfViewMiddleware", None),  # Explicit exclude
    ("Function/django.contrib.auth.middleware:AuthenticationMiddleware", 1),
    ("Function/django.contrib.messages.middleware:MessageMiddleware", 1),
    ("Function/django.middleware.gzip:GZipMiddleware", None),  # Explicit exclude
    ("Function/middleware:ExceptionTo410Middleware", 1),  # Still included (incomplete name does not capture this)
    ("Function/django.urls.resolvers:URLResolver.resolve", "present"),
]


@pytest.fixture(
    params=[
        (wildcard_exclude_specific_include_settings, scoped_metrics_wildcard_exclude_specific_include),
        (wildcard_exclude_wildcard_include_settings, scoped_metrics_wildcard_exclude_wildcard_include),
        (specific_exclude_specific_include_settings, scoped_metrics_specific_exclude_specific_include_settings),
        (specific_exclude_no_include_settings, scoped_metrics_specific_exclude_no_include_settings),
        (no_exclude_specific_include_settings, scoped_metrics_no_exclude_specific_include_settings),
        (
            no_dots_wildcard_exclude_specific_include_settings,
            scoped_metrics_no_dots_wildcard_exclude_specific_include_settings,
        ),
        (
            more_dots_wildcard_exclude_wildcard_include_settings,
            scoped_metrics_more_dots_wildcard_exclude_wildcard_include_settings,
        ),
        (
            fewer_dots_wildcard_exclude_wildcard_include_settings,
            scoped_metrics_fewer_dots_wildcard_exclude_wildcard_include_settings,
        ),
        (
            specific_dots_exclude_wildcard_no_dots_include_settings,
            scoped_metrics_specific_dots_exclude_wildcard_no_dots_include_settings,
        ),
        (no_dots_exclude_specific_dots_include_settings, scoped_metrics_no_dots_exclude_specific_dots_include_settings),
        (case_sensitive_and_incomplete_names_settings, scoped_metrics_case_sensitive_and_incomplete_names_settings),
    ],
    ids=[
        "wildcard_exclude_specific_include",
        "wildcard_exclude_wildcard_include",
        "specific_exclude_specific_include",
        "specific_exclude_no_include_settings",
        "no_exclude_specific_include_settings",
        "no_dots_wildcard_exclude_specific_include_settings",
        "more_dots_wildcard_exclude_wildcard_include_settings",
        "fewer_dots_wildcard_exclude_wildcard_include_settings",
        "specific_dots_exclude_wildcard_no_dots_include_settings",
        "no_dots_exclude_specific_dots_include_settings",
        "case_sensitive_and_incomplete_names_settings",
    ],
)
def settings_and_metrics(request):
    exclude_include_override_settings, middleware_scoped_metrics = request.param
    exclude_settings, include_settings = exclude_include_override_settings

    _default_settings["instrumentation.middleware.django.exclude"] = exclude_settings
    _default_settings["instrumentation.middleware.django.include"] = include_settings

    return _default_settings, middleware_scoped_metrics


@pytest.fixture
def settings_fixture(request, settings_and_metrics):
    _default_settings, _ = settings_and_metrics
    return _default_settings


@pytest.fixture
def middleware_scoped_metrics(request, settings_and_metrics):
    _, middleware_scoped_metrics = settings_and_metrics
    return [("Function/views:index", 1), *middleware_scoped_metrics]


@pytest.fixture
def middleware_rollup_metrics(request, settings_and_metrics):
    _, middleware_scoped_metrics = settings_and_metrics
    return [(f"Python/Framework/Django/{django.get_version()}", 1), *middleware_scoped_metrics]


@pytest.fixture
def application():
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    return AsgiTest(get_asgi_application())


collector_agent_registration = django_collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_django)", scope="function"
)


def test_wildcard_filters(application, middleware_scoped_metrics, middleware_rollup_metrics):
    @validate_transaction_count(1)
    @validate_transaction_metrics(
        "views:index", scoped_metrics=middleware_scoped_metrics, rollup_metrics=middleware_rollup_metrics
    )
    @validate_code_level_metrics("views", "index")
    def _test():
        response = application.get("/")
        assert response.status == 200

    _test()
