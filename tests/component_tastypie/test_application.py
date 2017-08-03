import django
import six
import webtest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors)

from wsgi import application

DJANGO_VERSION = tuple(map(int, django.get_version().split('.')[:2]))

test_application = webtest.TestApp(application)

_test_application_index_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Function/django.http.response:HttpResponse.close', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:index', 1),
]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:index',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index():
    response = test_application.get('/index/')
    assert response.status_code == 200
    response.mustcontain('INDEX RESPONSE')


_test_application_get_not_found_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Function/django.http.response:HttpResponseNotFound.close', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
]

if DJANGO_VERSION < (1, 10):
    _test_application_get_not_found_scoped_metrics.append(
            ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 1))
else:
    _test_application_get_not_found_scoped_metrics.append(
            ('Function/django.urls.resolvers:RegexURLResolver.resolve', 1))

if six.PY3:
    _test_application_get_not_found_scoped_metrics.append(
        ('Function/tastypie.resources:Resource.wrap_view.<locals>.wrapper', 1))
else:
    _test_application_get_not_found_scoped_metrics.append(
            ('Function/tastypie.resources:wrapper', 1))


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('api:SimpleResource.dispatch_detail',
        scoped_metrics=_test_application_get_not_found_scoped_metrics)
def test_get_not_found():
    test_application.get('/api/simple/100000/', status=404)
