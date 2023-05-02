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
from newrelic.core.config import global_settings
from testing_support.fixtures import (
        override_ignore_status_codes,
        override_generic_settings)
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors

SETTINGS = global_settings()


def test_basic(app):
    _test_basic_metrics = (
        ('Function/' + app.name_prefix + '.__call__', 1),
        ('Function/_target_application:Index.on_get', 1),
    )

    @validate_code_level_metrics("_target_application.Index", "on_get")
    @validate_transaction_metrics('_target_application:Index.on_get',
            scoped_metrics=_test_basic_metrics,
            rollup_metrics=_test_basic_metrics)
    def _test():
        response = app.get('/', status=200)
        response.mustcontain('ok')

    _test()


@override_ignore_status_codes([404])
@validate_transaction_errors(errors=[])
def test_ignored_status_code(app):

    @validate_transaction_metrics(app.name_prefix + '._handle_exception')
    def _test():
        app.get('/foobar', status=404)

    _test()


@override_ignore_status_codes([])
def test_error_recorded(app):

    @validate_transaction_errors(errors=[app.not_found_error])
    @validate_transaction_metrics(app.name_prefix + '._handle_exception')
    def _test():
        app.get('/foobar', status=404)

    _test()


# This test verifies that we don't actually break anything if somebody puts
# garbage into the status code
@validate_transaction_metrics('_target_application:BadResponse.on_get')
@validate_code_level_metrics("_target_application.BadResponse", "on_get")
@validate_transaction_errors(errors=['_target_application:BadGetRequest'])
def test_bad_response_error(app):
    # Disable linting since this should actually be an invalid response
    # (incorrect media type int)
    lint = app.lint
    app.lint = False
    try:
        app.get('/bad_response', status=200)
    finally:
        app.lint = lint


@validate_transaction_metrics('_target_application:BadResponse.on_put')
@validate_code_level_metrics("_target_application.BadResponse", "on_put")
@validate_transaction_errors(errors=['_target_application:BadPutRequest'])
def test_unhandled_exception(app):
    from falcon import __version__ as falcon_version

    # Falcon v3 and above will not raise an uncaught exception
    if int(falcon_version.split('.', 1)[0]) >= 3:
        app.put('/bad_response', status=500, expect_errors=True)
    else:
        with pytest.raises(app.BadPutRequest):
            app.put('/bad_response')


@override_generic_settings(SETTINGS, {
    'enabled': False,
})
def test_nr_disabled_ok(app):
    response = app.get('/', status=200)
    response.mustcontain('ok')


@override_generic_settings(SETTINGS, {
    'enabled': False,
})
def test_nr_disabled_error(app):
    app.get('/foobar', status=404)
