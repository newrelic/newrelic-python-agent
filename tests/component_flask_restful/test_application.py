import pytest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_ignore_status_codes)


def target_application(propagate_exceptions=False):
    from _test_application import get_test_application
    return get_test_application(propagate_exceptions)


_test_application_index_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:indexresource', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:indexresource',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index():
    application = target_application()
    response = application.get('/index')
    response.mustcontain('hello')


_test_application_raises_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Function/_test_application:exceptionresource', 1),
]


@pytest.mark.parametrize(
    'exception,status_code,ignore_status_code,propagate_exceptions', [
        ('werkzeug.exceptions:HTTPException', 404, False, False),
        ('werkzeug.exceptions:HTTPException', 404, True, False),
        ('werkzeug.exceptions:HTTPException', 503, False, False),
        ('_test_application:CustomException', 500, False, False),
        ('_test_application:CustomException', 500, False, True),
])
def test_application_raises(exception, status_code, ignore_status_code,
        propagate_exceptions):

    @validate_transaction_metrics('_test_application:exceptionresource',
            scoped_metrics=_test_application_raises_scoped_metrics)
    def _test():
        try:
            application = target_application(propagate_exceptions)
            application.get('/exception/%s/%i' % (exception,
                status_code), status=status_code, expect_errors=True)
        except:  # capture all exceptions because they are expected
            pass

    if ignore_status_code:
        _test = validate_transaction_errors(errors=[])(_test)
        _test = override_ignore_status_codes([status_code])(_test)
    else:
        _test = validate_transaction_errors(errors=[exception])(_test)
        _test = override_ignore_status_codes([])(_test)

    _test()
