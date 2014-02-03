from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors)

from newrelic.packages import six

import webtest

from bottle import route, error, default_app, __version__ as version

version = [int(x) for x in version.split('-')[0].split('.')]

if len(version) == 2:
    version.append(0)

version = tuple(version)

@route('/index')
def index_page():
    return 'INDEX RESPONSE'

@route('/error')
def error_page():
    raise RuntimeError('RUNTIME ERROR')

@error(404)
def error404_page(error):
    return 'NOT FOUND'

application = default_app()
test_application = webtest.TestApp(application)

_test_application_index_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/test_application:index_page', 1)]

if version >= (0, 9, 0):
    _test_application_index_scoped_metrics.extend([
        ('Function/bottle:Bottle.wsgi', 1)])
else:
    _test_application_index_scoped_metrics.extend([
        ('Function/bottle:Bottle.__call__', 1)])

_test_application_index_custom_metrics = [
        ('Python/Framework/Bottle/%s.%s.%s' % version, 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('test_application:index_page',
        scoped_metrics=_test_application_index_scoped_metrics,
        custom_metrics=_test_application_index_custom_metrics)
def test_application_index():
    response = test_application.get('/index')
    response.mustcontain('INDEX RESPONSE')

_test_application_error_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/test_application:error_page', 1)]

if version >= (0, 9, 0):
    _test_application_error_scoped_metrics.extend([
        ('Function/bottle:Bottle.wsgi', 1)])
else:
    _test_application_error_scoped_metrics.extend([
        ('Function/bottle:Bottle.__call__', 1)])

_test_application_error_custom_metrics = [
        ('Python/Framework/Bottle/%s.%s.%s' % version, 1)]

if six.PY3:
    _test_application_error_errors = ['builtins:RuntimeError']
else:
    _test_application_error_errors = ['exceptions:RuntimeError']

@validate_transaction_errors(errors=_test_application_error_errors)
@validate_transaction_metrics('test_application:error_page',
        scoped_metrics=_test_application_error_scoped_metrics,
        custom_metrics=_test_application_error_custom_metrics)
def test_application_error():
    response = test_application.get('/error', status=500, expect_errors=True)

_test_application_not_found_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/test_application:error404_page', 1)]

if version >= (0, 9, 0):
    _test_application_not_found_scoped_metrics.extend([
        ('Function/bottle:Bottle.wsgi', 1)])
else:
    _test_application_not_found_scoped_metrics.extend([
        ('Function/bottle:Bottle.__call__', 1)])

_test_application_not_found_custom_metrics = [
        ('Python/Framework/Bottle/%s.%s.%s' % version, 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('test_application:error404_page',
        scoped_metrics=_test_application_not_found_scoped_metrics,
        custom_metrics=_test_application_not_found_custom_metrics)
def test_application_not_found():
    response = test_application.get('/missing', status=404)
    response.mustcontain('NOT FOUND')
