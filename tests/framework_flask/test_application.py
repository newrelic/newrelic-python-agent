from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors)

try:
    # The __version__ attribute was only added in 0.7.0.
    from flask import __version__ as flask_version
    is_gt_flask060 = True
except ImportError:
    is_gt_flask060 = False

def target_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as we will then get view handler
    # functions are different between Python 2 and 3, with the latter
    # showing <local> scope in path.

    from _test_application import _test_application
    return _test_application

_test_application_index_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:index_page', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:index_page',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index():
    application = target_application()
    response = application.get('/index')
    response.mustcontain('INDEX RESPONSE')

_test_application_error_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:error_page', 1),
        ('Function/flask.app:Flask.handle_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

if is_gt_flask060:
    _test_application_error_scoped_metrics.extend([
            ('Function/flask.app:Flask.handle_user_exception', 1)])

@validate_transaction_errors(errors=['exceptions:RuntimeError'])
@validate_transaction_metrics('_test_application:error_page',
        scoped_metrics=_test_application_error_scoped_metrics)
def test_application_error():
    application = target_application()
    response = application.get('/error', status=500, expect_errors=True)

_test_application_abort_404_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:abort_404_page', 1),
        ('Function/flask.app:Flask.handle_http_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

if is_gt_flask060:
    _test_application_abort_404_scoped_metrics.extend([
            ('Function/flask.app:Flask.handle_user_exception', 1)])

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:abort_404_page',
        scoped_metrics=_test_application_abort_404_scoped_metrics)
def test_application_abort_404():
    application = target_application()
    response = application.get('/abort_404', status=404)

_test_application_exception_404_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:exception_404_page', 1),
        ('Function/flask.app:Flask.handle_http_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

if is_gt_flask060:
    _test_application_exception_404_scoped_metrics.extend([
            ('Function/flask.app:Flask.handle_user_exception', 1)])

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:exception_404_page',
        scoped_metrics=_test_application_exception_404_scoped_metrics)
def test_application_exception_404():
    application = target_application()
    response = application.get('/exception_404', status=404)

_test_application_not_found_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/flask.app:Flask.handle_http_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

if is_gt_flask060:
    _test_application_not_found_scoped_metrics.extend([
            ('Function/flask.app:Flask.handle_user_exception', 1)])

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('flask.app:Flask.handle_http_exception',
        scoped_metrics=_test_application_not_found_scoped_metrics)
def test_application_not_found():
    application = target_application()
    response = application.get('/missing', status=404)

_test_application_render_template_string_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:template_string', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
        ('Template/Compile/<template>', 1),
        ('Template/Render/<template>', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:template_string',
        scoped_metrics=_test_application_render_template_string_scoped_metrics)
def test_application_render_template_string():
    application = target_application()
    response = application.get('/template_string')

_test_application_render_template_not_found_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:template_not_found', 1),
        ('Function/flask.app:Flask.handle_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

if is_gt_flask060:
    _test_application_render_template_not_found_scoped_metrics.extend([
            ('Function/flask.app:Flask.handle_user_exception', 1)])

@validate_transaction_errors(errors=['jinja2.exceptions:TemplateNotFound'])
@validate_transaction_metrics('_test_application:template_not_found',
        scoped_metrics=_test_application_render_template_not_found_scoped_metrics)
def test_application_render_template_not_found():
    application = target_application()
    response = application.get('/template_not_found', status=500)
