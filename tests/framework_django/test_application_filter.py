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

# import random
import django
import pytest
from testing_support.fixtures import (
    override_application_settings,
    override_generic_settings,
    override_ignore_status_codes,
    collector_agent_registration_fixture,
    collector_available_fixture,
)
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics

# from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_count import validate_transaction_count

# from newrelic.common.encoding_utils import gzip_decompress
from newrelic.core.config import global_settings
from newrelic.core.agent import agent_instance

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
    # "instrumentation.django_middleware.exclude": [
    #     "django.middleware.*",
    #     "django.contrib.messages.middleware:MessageMiddleware",
    # ],
    # "instrumentation.django_middleware.include": ["django.middleware.csrf:CsrfViewMiddleware"],
    # "instrumentation.django_middleware.include": ["django.middleware.*", "django.middleware.co*", "django.contrib.messages.middleware:MessageMiddleware"],
    # "instrumentation.django_middleware.exclude": ["django.middleware.c*"],
}

wildcard_exclude_specific_include = (
    # (
    ["django.middleware.*", "django.contrib.messages.middleware:MessageMiddleware"],
    ["django.middleware.csrf:CsrfViewMiddleware"]
    # ),
)
wildcard_exclude_wildcard_include = (
    # (
    ["django.middleware.c*"],
    ["django.middleware.*", "django.middleware.co*", "django.contrib.messages.middleware:MessageMiddleware"],
    # ),
)


# # @pytest.fixture(params=[wildcard_exclude_specific_include, wildcard_exclude_wildcard_include])
# @pytest.fixture(params=(wildcard_exclude_specific_include))
# def collector_agent_registration(request):
# # def collector_agent_registration(wildcard_exclude_specific_include):
#     """
#     Fixture to register the collector agent with the default settings for Django ASGI tests.
#     """
#     breakpoint()
#     # agent_instance()._applications = {}  # Reset applications to avoid interference from other tests
#     _default_settings = {
#         "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
#         "transaction_tracer.explain_threshold": 0.0,
#         "transaction_tracer.transaction_threshold": 0.0,
#         "transaction_tracer.stack_trace_threshold": 0.0,
#         "debug.log_data_collector_payloads": True,
#         "debug.record_transaction_failure": True,
#         "debug.log_autorum_middleware": True,
#         "feature_flag": {"django.instrumentation.inclusion-tags.r1"},
#         "instrumentation.django_middleware.exclude": request.param[0],
#         "instrumentation.django_middleware.include": request.param[1],
#         # "instrumentation.django_middleware.exclude": ["django.middleware.*", "django.contrib.messages.middleware:MessageMiddleware"],
#         # "instrumentation.django_middleware.include": ["django.middleware.csrf:CsrfViewMiddleware"],
#         # "instrumentation.django_middleware.include": ["django.middleware.*", "django.middleware.co*", "django.contrib.messages.middleware:MessageMiddleware"],
#         # "instrumentation.django_middleware.exclude": ["django.middleware.c*"],
#     }
    
#     return collector_agent_registration_fixture(
#         app_name=f"Python Agent Test (framework_django)", default_settings=_default_settings, scope="function"
#     )

collector_agent_registration = collector_agent_registration_fixture(
    app_name=f"Python Agent Test (framework_django)", default_settings=_default_settings, scope="function"
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

# scoped_metrics = scoped_metrics_wildcard_exclude_specific_include

# rollup_metrics = scoped_metrics + [(f"Python/Framework/Django/{django.get_version()}", 1)]


@pytest.fixture(scope="function")
def application():
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    return AsgiTest(get_asgi_application())


def target_application():
    from _target_application import _target_application

    return _target_application


@pytest.mark.parametrize("scoped_metrics,middleware_exclude_settings,middleware_include_settings", [
    (
        scoped_metrics_wildcard_exclude_specific_include,
        ["django.middleware.*", "django.contrib.messages.middleware:MessageMiddleware"],
        ["django.middleware.csrf:CsrfViewMiddleware"],
    ),
    (
        scoped_metrics_wildcard_exclude_wildcard_include,
        ["django.middleware.c*"],
        ["django.middleware.*", "django.middleware.co*", "django.contrib.messages.middleware:MessageMiddleware"]
    ),
])
def test_asgi_application_filter(
    application,
    scoped_metrics,
    middleware_exclude_settings,
    middleware_include_settings
):
    """
    Test the ASGI application with different middleware include and exclude settings.
    """
    # override_application_settings(
    #     {
    #         "instrumentation.django_middleware.exclude": middleware_exclude_settings,
    #         "instrumentation.django_middleware.include": middleware_include_settings,
    #     }
    # )
    override_generic_settings(
        global_settings(),
        {
            "instrumentation.django_middleware.exclude": middleware_exclude_settings,
            "instrumentation.django_middleware.include": middleware_include_settings,
        }
    )
    @validate_transaction_count(1)
    @validate_transaction_metrics(
        "views:index",
        scoped_metrics=[("Function/views:index", 1)] + scoped_metrics,
        rollup_metrics=scoped_metrics + [(f"Python/Framework/Django/{django.get_version()}", 1)]
    )
    @validate_code_level_metrics("views", "index")
    def _test():
        response = application.get("/")
        assert response.status == 200

    _test()


# # @override_generic_settings(global_settings(), {
# #     "instrumentation.django_middleware.include": ["django.middleware.*", "django.middleware.co*", "django.contrib.messages.middleware:MessageMiddleware"],
# #     "instrumentation.django_middleware.exclude": ["django.middleware.c*"],
# # })
# @validate_transaction_metrics(
#     "views:index", scoped_metrics=[("Function/views:index", 1)] + scoped_metrics, rollup_metrics=scoped_metrics + [(f"Python/Framework/Django/{django.get_version()}", 1)]
# )
# @validate_code_level_metrics("views", "index")
# def test_asgi_index(application):
#     response = application.get("/")
#     assert response.status == 200


# @validate_transaction_errors(errors=[])
# @override_generic_settings(global_settings(), {
#     "instrumentation.django_middleware.exclude": wildcard_exclude_specific_include[0],
#     "instrumentation.django_middleware.include": wildcard_exclude_specific_include[1],
# })

# collector_agent_registration = collector_agent_registration_fixture(
#     app_name=f"Python Agent Test (framework_django)", default_settings=_default_settings, scope="function"
# )

# @validate_transaction_metrics(
#     "views:index",
#     scoped_metrics=scoped_metrics_wildcard_exclude_specific_include,
#     rollup_metrics=scoped_metrics_wildcard_exclude_specific_include
#     + [(f"Python/Framework/Django/{django.get_version()}", 1)],
# )
# @validate_code_level_metrics("views", "index")
# def test_application_index():
#     test_application = target_application()
#     response = test_application.get("")
#     response.mustcontain("INDEX RESPONSE")

# agent_instance()._applications = {}  # Reset applications to avoid interference from other tests

