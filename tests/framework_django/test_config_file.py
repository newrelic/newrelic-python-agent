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
import tempfile
from importlib import reload

import django
import pytest
from testing_support.fixtures import Environ, collector_available_fixture, django_collector_agent_registration_fixture

import newrelic.config
import newrelic.core.config
from newrelic.common.object_wrapper import function_wrapper
from newrelic.config import initialize
from newrelic.core.config import global_settings

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


@pytest.fixture
def application():
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    return AsgiTest(get_asgi_application())


@pytest.fixture
def settings_fixture():
    return _default_settings


collector_agent_registration = django_collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_django)", scope="function"
)


def reset_agent_config(ini_contents, env_dict):
    @function_wrapper
    def reset(wrapped, instance, args, kwargs):
        with Environ(env_dict):
            ini_file = tempfile.NamedTemporaryFile()
            ini_file.write(ini_contents)
            ini_file.seek(0)

            # clean settings cache and reload env vars
            # Note that reload can at times work in unexpected ways. All that
            # is required here is that the globals (such as
            # newrelic.core.config._settings) be reset.
            #
            # From python docs (2.x and 3.x)
            # "When a module is reloaded, its dictionary (containing the
            # module's global variables) is retained. Redefinitions of names
            # will override the old definitions, so this is generally not a
            # problem."
            reload(newrelic.core.config)
            reload(newrelic.config)
            initialize(ini_file.name)
            newrelic.config._reset_configuration_done()
            returned = wrapped(*args, **kwargs)

        return returned

    return reset


INI_FILE_WILDCARD_EXCLUDE_SPECIFIC_INCLUDE = b"""
[newrelic]
instrumentation.middleware.django.exclude = django.middleware.* django.contrib.messages.middleware:MessageMiddleware
instrumentation.middleware.django.include = django.middleware.csrf:CsrfViewMiddleware
"""

INI_FILE_WILDCARD_EXCLUDE_WILDCARD_INCLUDE = b"""
[newrelic]
instrumentation.middleware.django.exclude = django.middleware.c*
instrumentation.middleware.django.include = django.middleware.* django.middleware.co* django.contrib.messages.middleware:MessageMiddleware
"""

INI_FILE_MIDDLEWARE_DISABLED = b"""
[newrelic]
instrumentation.middleware.django.enabled = False
instrumentation.middleware.django.exclude = django.middleware.c*
instrumentation.middleware.django.include = django.middleware.* django.middleware.co* django.contrib.messages.middleware:MessageMiddleware
"""


@reset_agent_config(INI_FILE_WILDCARD_EXCLUDE_SPECIFIC_INCLUDE, {})
def test_config_settings(application):
    settings = global_settings()
    response = application.get("/")
    assert response.status == 200
    assert settings.instrumentation.middleware.django.enabled  # `True` is default setting
    assert settings.instrumentation.middleware.django.exclude == [
        "django.middleware.*",
        "django.contrib.messages.middleware:MessageMiddleware",
    ]
    assert settings.instrumentation.middleware.django.include == ["django.middleware.csrf:CsrfViewMiddleware"]


@reset_agent_config(
    INI_FILE_WILDCARD_EXCLUDE_WILDCARD_INCLUDE, {"NEW_RELIC_INSTRUMENTATION_DJANGO_MIDDLEWARE_ENABLED": False}
)
def test_override_config_settings(application):
    """
    Test the priority of include/exclude settings.
    The default setting is True.
    Environment variable should override this setting.
    """
    settings = global_settings()
    response = application.get("/")
    assert response.status == 200
    assert not settings.instrumentation.middleware.django.enabled
    assert settings.instrumentation.middleware.django.exclude == ["django.middleware.c*"]
    assert settings.instrumentation.middleware.django.include == [
        "django.middleware.*",
        "django.middleware.co*",
        "django.contrib.messages.middleware:MessageMiddleware",
    ]


@reset_agent_config(INI_FILE_MIDDLEWARE_DISABLED, {"NEW_RELIC_INSTRUMENTATION_DJANGO_MIDDLEWARE_ENABLED": True})
def test_disabled_middleware_settings(application):
    """
    Test the priority of include/exclude settings.
    The agent config file takes precedence over the environment variable
    """
    settings = global_settings()
    response = application.get("/")
    assert response.status == 200
    assert not settings.instrumentation.middleware.django.enabled
    assert settings.instrumentation.middleware.django.exclude == ["django.middleware.c*"]
    assert settings.instrumentation.middleware.django.include == [
        "django.middleware.*",
        "django.middleware.co*",
        "django.contrib.messages.middleware:MessageMiddleware",
    ]
