import pytest
from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors, override_ignore_status_codes,
        override_generic_settings)

SETTINGS = global_settings()

_test_basic_metrics = (
    ('Function/falcon.api:API.__call__', 1),
    ('Function/_target_application:Index.on_get', 1),
)


@validate_transaction_metrics('_target_application:Index.on_get',
        scoped_metrics=_test_basic_metrics,
        rollup_metrics=_test_basic_metrics)
def test_basic(app):
    response = app.get('/', status=200)
    response.mustcontain('ok')


@validate_transaction_metrics('falcon.api:API._handle_exception')
@override_ignore_status_codes([404])
@validate_transaction_errors(errors=[])
def test_ignored_status_code(app):
    app.get('/foobar', status=404)


@validate_transaction_metrics('falcon.api:API._handle_exception')
@override_ignore_status_codes([])
@validate_transaction_errors(errors=['falcon.errors:HTTPNotFound'])
def test_error_recorded(app):
    app.get('/foobar', status=404)


# This test verifies that we don't actually break anything if somebody puts
# garbage into the status code
@validate_transaction_metrics('_target_application:BadResponse.on_get')
@validate_transaction_errors(errors=['_target_application:Oops'])
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
@validate_transaction_errors(errors=['_target_application:Crash'])
def test_unhandled_exception(app):
    with pytest.raises(app.Crash):
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
