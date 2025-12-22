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
import os
from pathlib import Path

from conftest import async_handler_support, skip_if_not_async_handler_support
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_error_event_attributes import validate_error_event_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.fixtures import dt_enabled

os.environ["NEW_RELIC_CONFIG_FILE"] = str(Path(__file__).parent / "newrelic_flask.ini")

try:
    # The __version__ attribute was only added in 0.7.0.
    # Flask team does not use semantic versioning during development.
    from flask import __version__ as flask_version

    flask_version = tuple([int(v) for v in flask_version.split(".")])
    is_gt_flask060 = True
    is_dev_version = False
except ValueError:
    is_gt_flask060 = True
    is_dev_version = True
except ImportError:
    is_gt_flask060 = False
    is_dev_version = False

requires_endpoint_decorator = pytest.mark.skipif(not is_gt_flask060, reason="The endpoint decorator is not supported.")

def target_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late.

    if not async_handler_support:
        from _test_otel_application import _test_application
    else:
        from _test_otel_application_async import _test_application
    return _test_application


_exact_intrinsics = {"type": "Span"}
_exact_root_intrinsics = _exact_intrinsics.copy().update({"nr.entryPoint": True})
_expected_intrinsics = ["traceId", "transactionId", "sampled", "priority", "timestamp", "duration", "name", "category", "guid"]
_expected_root_intrinsics = [*_expected_intrinsics.copy(), "transaction.name"]
_expected_child_intrinsics = [*_expected_intrinsics.copy(), "parentId"]
_unexpected_root_intrinsics = ["parentId"]
_unexpected_child_intrinsics = ["nr.entryPoint", "transaction.name"]

_test_application_rollup_metrics = [
    ("Supportability/DistributedTrace/CreatePayload/Success", 1),
    ("Supportability/TraceContext/Create/Success", 1),
    ("Python/WSGI/Input/Bytes", 1),
    ("Python/WSGI/Input/Time", 1),
    ("Python/WSGI/Input/Calls/read", 1),
    ("Python/WSGI/Input/Calls/readline", 1),
    ("Python/WSGI/Input/Calls/readlines", 1),
    ("Python/WSGI/Output/Bytes", 1),
    ("Python/WSGI/Output/Time", 1),
    ("Python/WSGI/Output/Calls/yield", 1),
    ("Python/WSGI/Output/Calls/write", 1),
    ("HttpDispatcher", 1),
    ("WebTransaction", 1),
    ("WebTransactionTotalTime", 1),
]

_test_application_index_scoped_metrics = [
    ("Function/GET /index", 1),
]


@dt_enabled
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "index",
    group="Uri",
    scoped_metrics=_test_application_index_scoped_metrics,
    rollup_metrics=_test_application_rollup_metrics + _test_application_index_scoped_metrics,
)
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
)
def test_otel_application_index():
    application = target_application()
    response = application.get("/index")
    response.mustcontain("INDEX RESPONSE")


_test_application_async_scoped_metrics = [
    ("Function/GET /async", 1),
]

@skip_if_not_async_handler_support
@dt_enabled
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "async",
    group="Uri",
    scoped_metrics=_test_application_async_scoped_metrics,
    rollup_metrics=_test_application_rollup_metrics + _test_application_async_scoped_metrics,
)
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
)
def test_otel_application_async():
    application = target_application()
    response = application.get("/async")
    response.mustcontain("ASYNC RESPONSE")


_test_application_endpoint_scoped_metrics = [
    ("Function/GET /endpoint", 1),
]

@dt_enabled
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "endpoint",
    group="Uri",
    scoped_metrics=_test_application_endpoint_scoped_metrics,
    rollup_metrics=_test_application_rollup_metrics + _test_application_endpoint_scoped_metrics,
)
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
)
def test_otel_application_endpoint():
    application = target_application()
    response = application.get("/endpoint")
    response.mustcontain("ENDPOINT RESPONSE")


_test_application_error_scoped_metrics = [
    ("Function/GET /error", 1),
]

@dt_enabled
@validate_transaction_errors(errors=["builtins:RuntimeError"])
@validate_error_event_attributes(
    exact_attrs={
        "agent": {},
        "intrinsic": {"error.message": "RUNTIME ERROR", "error.class": "builtins:RuntimeError", "error.expected": False},
        "user": {"exception.escaped": False},
    }
)
@validate_transaction_metrics(
    "error",
    group="Uri",
    scoped_metrics=_test_application_error_scoped_metrics,
    rollup_metrics=_test_application_rollup_metrics + _test_application_error_scoped_metrics,
)
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
)
def test_otel_application_error():
    application = target_application()
    application.get("/error", status=500, expect_errors=True)


_test_application_abort_404_scoped_metrics = [
    ("Function/GET /abort_404", 1),
]

@dt_enabled
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "abort_404",
    group="Uri",
    scoped_metrics=_test_application_abort_404_scoped_metrics,
    rollup_metrics=_test_application_rollup_metrics + _test_application_abort_404_scoped_metrics,
)
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
)
def test_otel_application_abort_404():
    application = target_application()
    application.get("/abort_404", status=404)


_test_application_exception_404_scoped_metrics = [
    ("Function/GET /exception_404", 1),
]

@dt_enabled
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "exception_404",
    group="Uri",
    scoped_metrics=_test_application_exception_404_scoped_metrics,
    rollup_metrics=_test_application_rollup_metrics + _test_application_exception_404_scoped_metrics,
)
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
)
def test_application_exception_404():
    application = target_application()
    application.get("/exception_404", status=404)


_test_application_not_found_scoped_metrics = [
    ("Function/GET /missing", 1),
]

@dt_enabled
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "missing",
    group="Uri",
    scoped_metrics=_test_application_not_found_scoped_metrics,
    rollup_metrics=_test_application_rollup_metrics + _test_application_not_found_scoped_metrics,
)
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
)
def test_application_not_found():
    application = target_application()
    application.get("/missing", status=404)


_test_application_render_template_string_scoped_metrics = [
    ("Function/GET /template_string", 1),
    ("Template/Compile/<template>", 1),
    ("Template/Render/<template>", 1),
]

@dt_enabled
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "template_string",
    group="Uri",
    scoped_metrics=_test_application_render_template_string_scoped_metrics,
    rollup_metrics=_test_application_rollup_metrics + _test_application_render_template_string_scoped_metrics,
)
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    count=3,
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
)
def test_application_render_template_string():
    application = target_application()
    application.get("/template_string")


_test_application_render_template_not_found_scoped_metrics = [
    ("Function/GET /template_not_found", 1),
]


@dt_enabled
@validate_transaction_errors(errors=["jinja2.exceptions:TemplateNotFound"])
@validate_error_event_attributes(
    exact_attrs={
        "agent": {},
        "intrinsic": {"error.message": "not_found", "error.class": "jinja2.exceptions:TemplateNotFound", "error.expected": False},
        "user": {"exception.escaped": False},
    }
)
@validate_transaction_metrics(
    "template_not_found",
    group="Uri",
    scoped_metrics=_test_application_render_template_not_found_scoped_metrics,
    rollup_metrics=_test_application_rollup_metrics + _test_application_render_template_not_found_scoped_metrics,
)
@validate_span_events(
    exact_intrinsics=_exact_root_intrinsics,
    expected_intrinsics=_expected_root_intrinsics,
    unexpected_intrinsics=_unexpected_root_intrinsics,
)
@validate_span_events(
    exact_intrinsics=_exact_intrinsics,
    expected_intrinsics=_expected_child_intrinsics,
    unexpected_intrinsics=_unexpected_child_intrinsics,
)
def test_application_render_template_not_found():
    application = target_application()
    application.get("/template_not_found", status=500, expect_errors=True)

