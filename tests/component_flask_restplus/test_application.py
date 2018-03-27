import pytest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_ignore_status_codes,
    override_generic_settings)

from newrelic.core.config import global_settings


def target_application():
    from _test_application import test_application
    return test_application


_test_application_index_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:index_resource', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:index_resource',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index():
    application = target_application()
    response = application.get('/index')
    response.mustcontain('hello')


_test_application_raises_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:exception_resource', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
]


@pytest.mark.parametrize('exception,status_code,ignore_status_code', [
    ('werkzeug.exceptions:HTTPException', 404, False),
    ('werkzeug.exceptions:HTTPException', 404, True),
    ('werkzeug.exceptions:HTTPException', 503, False),
    ('_test_application:CustomException', 500, False),
])
def test_application_raises(exception, status_code, ignore_status_code):

    @validate_transaction_metrics('_test_application:exception_resource',
            scoped_metrics=_test_application_raises_scoped_metrics)
    def _test():
        application = target_application()
        application.get('/exception/%s/%i' % (exception,
            status_code), status=status_code, expect_errors=True)

    if ignore_status_code:
        _test = validate_transaction_errors(errors=[])(_test)
        _test = override_ignore_status_codes([status_code])(_test)
    else:
        _test = validate_transaction_errors(errors=[exception])(_test)
        _test = override_ignore_status_codes([])(_test)

    _test()


def test_application_outside_transaction():

    _settings = global_settings()

    @override_generic_settings(_settings, {'enabled': False})
    def _test():
        application = target_application()
        application.get('/exception/werkzeug.exceptions:HTTPException/404',
                status=404)

    _test()
