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

import base64

import pytest
import webtest
from bottle import __version__ as version
from testing_support.fixtures import override_application_settings, override_ignore_status_codes
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.common.package_version_utils import get_package_version_tuple

version = list(get_package_version_tuple("bottle"))

if len(version) == 2:
    version.append(0)

version = tuple(version)
assert version > (0, 1), "version information not found"

version_metrics = [(f"Python/Framework/Bottle/{'.'.join(str(v) for v in version)}", 1)]

requires_auth_basic = pytest.mark.skipif(version < (0, 9, 0), reason="Bottle only added auth_basic in 0.9.0.")
requires_plugins = pytest.mark.skipif(version < (0, 9, 0), reason="Bottle only added auth_basic in 0.9.0.")

_test_application_index_scoped_metrics = [
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_target_application:index_page", 1),
]

if version >= (0, 9, 0):
    _test_application_index_scoped_metrics.extend([("Function/bottle:Bottle.wsgi", 1)])
else:
    _test_application_index_scoped_metrics.extend([("Function/bottle:Bottle.__call__", 1)])

_test_application_index_custom_metrics = version_metrics.copy()


@validate_code_level_metrics("_target_application", "index_page")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "_target_application:index_page",
    scoped_metrics=_test_application_index_scoped_metrics,
    custom_metrics=_test_application_index_custom_metrics,
)
def test_application_index(target_application):
    response = target_application.get("/index")
    response.mustcontain("INDEX RESPONSE")


_test_application_error_scoped_metrics = [
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_target_application:error_page", 1),
]

if version >= (0, 9, 0):
    _test_application_error_scoped_metrics.extend([("Function/bottle:Bottle.wsgi", 1)])
else:
    _test_application_error_scoped_metrics.extend([("Function/bottle:Bottle.__call__", 1)])

_test_application_error_custom_metrics = version_metrics.copy()
_test_application_error_errors = ["builtins:RuntimeError"]


@validate_code_level_metrics("_target_application", "error_page")
@validate_transaction_errors(errors=_test_application_error_errors)
@validate_transaction_metrics(
    "_target_application:error_page",
    scoped_metrics=_test_application_error_scoped_metrics,
    custom_metrics=_test_application_error_custom_metrics,
)
def test_application_error(target_application):
    response = target_application.get("/error", status=500, expect_errors=True)


_test_application_not_found_scoped_metrics = [
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_target_application:error404_page", 1),
]

if version >= (0, 9, 0):
    _test_application_not_found_scoped_metrics.extend([("Function/bottle:Bottle.wsgi", 1)])
else:
    _test_application_not_found_scoped_metrics.extend([("Function/bottle:Bottle.__call__", 1)])

_test_application_not_found_custom_metrics = version_metrics.copy()


@validate_code_level_metrics("_target_application", "error404_page")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "_target_application:error404_page",
    scoped_metrics=_test_application_not_found_scoped_metrics,
    custom_metrics=_test_application_not_found_custom_metrics,
)
def test_application_not_found(target_application):
    response = target_application.get("/missing", status=404)
    response.mustcontain("NOT FOUND")


_test_application_auth_basic_fail_scoped_metrics = [
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_target_application:auth_basic_page", 1),
]

if version >= (0, 9, 0):
    _test_application_auth_basic_fail_scoped_metrics.extend([("Function/bottle:Bottle.wsgi", 1)])
else:
    _test_application_auth_basic_fail_scoped_metrics.extend([("Function/bottle:Bottle.__call__", 1)])

_test_application_auth_basic_fail_custom_metrics = version_metrics.copy()


@requires_auth_basic
@validate_code_level_metrics("_target_application", "auth_basic_page")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "_target_application:auth_basic_page",
    scoped_metrics=_test_application_auth_basic_fail_scoped_metrics,
    custom_metrics=_test_application_auth_basic_fail_custom_metrics,
)
def test_application_auth_basic_fail(target_application):
    response = target_application.get("/auth", status=401)


_test_application_auth_basic_okay_scoped_metrics = [
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_target_application:auth_basic_page", 1),
]

if version >= (0, 9, 0):
    _test_application_auth_basic_okay_scoped_metrics.extend([("Function/bottle:Bottle.wsgi", 1)])
else:
    _test_application_auth_basic_okay_scoped_metrics.extend([("Function/bottle:Bottle.__call__", 1)])

_test_application_auth_basic_okay_custom_metrics = version_metrics.copy()


@requires_auth_basic
@validate_code_level_metrics("_target_application", "auth_basic_page")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "_target_application:auth_basic_page",
    scoped_metrics=_test_application_auth_basic_okay_scoped_metrics,
    custom_metrics=_test_application_auth_basic_okay_custom_metrics,
)
def test_application_auth_basic_okay(target_application):
    authorization_value = base64.b64encode(b"user:password").decode("Latin-1")
    environ = {"HTTP_AUTHORIZATION": f"Basic {authorization_value}"}
    response = target_application.get("/auth", extra_environ=environ)
    response.mustcontain("AUTH OKAY")


_test_application_plugin_error_scoped_metrics = [
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_target_application:plugin_error_page", 1),
]

if version >= (0, 9, 0):
    _test_application_plugin_error_scoped_metrics.extend([("Function/bottle:Bottle.wsgi", 1)])
else:
    _test_application_plugin_error_scoped_metrics.extend([("Function/bottle:Bottle.__call__", 1)])

_test_application_plugin_error_custom_metrics = version_metrics.copy()


@requires_plugins
@validate_code_level_metrics("_target_application", "plugin_error_page")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "_target_application:plugin_error_page",
    scoped_metrics=_test_application_plugin_error_scoped_metrics,
    custom_metrics=_test_application_plugin_error_custom_metrics,
)
@override_ignore_status_codes([403])
def test_application_plugin_error_ignore(target_application):
    response = target_application.get("/plugin_error", status=403, expect_errors=True)


@requires_plugins
@validate_code_level_metrics("_target_application", "plugin_error_page")
@validate_transaction_errors(errors=["bottle:HTTPError"])
@validate_transaction_metrics(
    "_target_application:plugin_error_page",
    scoped_metrics=_test_application_plugin_error_scoped_metrics,
    custom_metrics=_test_application_plugin_error_custom_metrics,
)
def test_application_plugin_error_capture(target_application):
    import newrelic.agent

    response = target_application.get("/plugin_error", status=403, expect_errors=True)


_test_html_insertion_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_settings)
def test_html_insertion(target_application):
    response = target_application.get("/html_insertion")

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # header added by the agent.

    response.mustcontain("NREUM HEADER", "NREUM.info")
