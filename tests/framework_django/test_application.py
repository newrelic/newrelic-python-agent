import webtest

from testing_support.fixtures import validate_transaction_metrics

from wsgi import application

from newrelic.packages import six

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
    if six.PY3:
        _test_application_index_scoped_metrics.extend([
                ('Function/django.http.response:HttpResponseBase.close', 1)])
    else:
        _test_application_index_scoped_metrics.extend([
                ('Function/django.http.response:HttpResponse.close', 1)])

@validate_transaction_metrics('views:index',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index():
    response = test_application.get('')
    response.mustcontain('INDEX RESPONSE')
