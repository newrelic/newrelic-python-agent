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

import pytest

from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
    override_generic_settings,
    override_ignore_status_codes,
)
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_autorum_middleware": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_django)", default_settings=_default_settings, scope="module"
)

@pytest.fixture
def database(autouse=True):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    import django

    django.setup()
    from django.core.management import call_command

    call_command("migrate", verbosity=0, interactive=False, run_syncdb=True)

def target_application():
    from _target_application import _target_application

    return _target_application


@validate_transaction_metrics(
    "views:index",
    scoped_metrics=[
        ("Function/django.core.handlers.wsgi:WSGIHandler.__call__", 1),
        ("Python/WSGI/Application", 1),
        ("Python/WSGI/Response", 1),
        ("Python/WSGI/Finalize", 1),
        ("Function/views:index", 1),
    ]
)
def test_home():
    test_application = target_application()
    response = test_application.get("")


@validate_transaction_metrics(
    "views:index",
    scoped_metrics=[
        ("Function/django.core.handlers.wsgi:WSGIHandler.__call__", 1),
        ("Python/WSGI/Application", 1),
        ("Python/WSGI/Response", 1),
        ("Python/WSGI/Finalize", 1),
        ("Function/views:index", 1),
    ]
)
def test_routable():
    test_application = target_application()
    response = test_application.get("/routable")


@validate_transaction_metrics(
    "views:index",
    scoped_metrics=[
        ("Function/django.core.handlers.wsgi:WSGIHandler.__call__", 1),
        ("Python/WSGI/Application", 1),
        ("Python/WSGI/Response", 1),
        ("Python/WSGI/Finalize", 1),
        ("Function/views:index", 1),
    ]
)
def test_routable_routable():
    test_application = target_application()
    response = test_application.get("/routable/routable")
