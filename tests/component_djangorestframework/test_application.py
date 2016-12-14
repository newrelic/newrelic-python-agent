import webtest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors)

from wsgi import application

import django

DJANGO_VERSION = tuple(map(int, django.get_version().split('.')[:2]))

test_application = webtest.TestApp(application)

_test_application_index_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:index', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_request', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_request', 1),
        ('Function/django.contrib.auth.middleware:AuthenticationMiddleware.process_request', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_request', 1),
        ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_view', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_response', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_response', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_response', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_response', 1),
        ('Function/newrelic.hooks.framework_django:browser_timing_middleware', 1)]

if DJANGO_VERSION >= (1, 5):
    _test_application_index_scoped_metrics.extend([
            ('Function/django.http.response:HttpResponse.close', 1)])

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:index',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index():
    response = test_application.get('')
    response.mustcontain('INDEX RESPONSE')

_test_application_view_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/urls:View.get', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_request', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_request', 1),
        ('Function/django.contrib.auth.middleware:AuthenticationMiddleware.process_request', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_request', 1),
        ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_view', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_response', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_response', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_response', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_response', 1),
        ('Function/newrelic.hooks.framework_django:browser_timing_middleware', 1)]

if DJANGO_VERSION >= (1, 5):
    _test_application_view_scoped_metrics.extend([
            ('Function/rest_framework.response:Response.close', 1)])

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('urls:View.get',
    scoped_metrics=_test_application_view_scoped_metrics)
def test_application_view():
    response = test_application.get('/view/')
    assert response.status_int == 200

_test_application_view_error_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/urls:ViewError.get', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_request', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_request', 1),
        ('Function/django.contrib.auth.middleware:AuthenticationMiddleware.process_request', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_request', 1),
        ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_view', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_response', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_response', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_response', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_response', 1),
        ('Function/newrelic.hooks.framework_django:browser_timing_middleware', 1)]

@validate_transaction_errors(errors=['urls:Error'])
@validate_transaction_metrics('urls:ViewError.get',
    scoped_metrics=_test_application_view_error_scoped_metrics)
def test_application_view_error():
    test_application.get('/view_error/', status=500)
