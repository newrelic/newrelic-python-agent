import pytest
from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors, override_ignore_status_codes,
        override_generic_settings)

SETTINGS = global_settings()


def test_basic(app):
    _test_basic_metrics = (
        ('Function/' + app.name_prefix + '.__call__', 1),
        ('Function/_target_application:Index.on_get', 1),
    )

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
