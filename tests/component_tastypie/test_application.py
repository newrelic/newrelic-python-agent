import django
import pytest
import six
import webtest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_ignore_status_codes)

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


_test_application_not_found_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Function/django.http.response:HttpResponseNotFound.close', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
]

if DJANGO_VERSION < (1, 10):
    _test_application_not_found_scoped_metrics.append(
            ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 1))
else:
    _test_application_not_found_scoped_metrics.append(
            ('Function/django.urls.resolvers:RegexURLResolver.resolve', 1))

if six.PY3:
    _test_application_not_found_scoped_metrics.append(
        ('Function/tastypie.resources:Resource.wrap_view.<locals>.wrapper', 1))
else:
    _test_application_not_found_scoped_metrics.append(
            ('Function/tastypie.resources:wrapper', 1))


@pytest.mark.parametrize('api_version', ['v1', 'v2'])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('api:SimpleResource.dispatch_detail',
        scoped_metrics=_test_application_not_found_scoped_metrics)
def test_not_found(api_version):
    test_application.get('/api/%s/simple/NotFound/' % api_version, status=404)


_test_application_object_does_not_exist_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Function/tastypie.http:HttpNotFound.close', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
]

if DJANGO_VERSION < (1, 10):
    _test_application_object_does_not_exist_scoped_metrics.append(
            ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 1))
else:
    _test_application_object_does_not_exist_scoped_metrics.append(
            ('Function/django.urls.resolvers:RegexURLResolver.resolve', 1))

if six.PY3:
    _test_application_object_does_not_exist_scoped_metrics.append(
        ('Function/tastypie.resources:Resource.wrap_view.<locals>.wrapper', 1))
else:
    _test_application_object_does_not_exist_scoped_metrics.append(
            ('Function/tastypie.resources:wrapper', 1))


@pytest.mark.parametrize('api_version', ['v1', 'v2'])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('api:SimpleResource.dispatch_detail',
        scoped_metrics=_test_application_object_does_not_exist_scoped_metrics)
def test_object_does_not_exist(api_version):
    test_application.get('/api/%s/simple/ObjectDoesNotExist/' % api_version,
            status=404)


_test_application_raises_zerodivision = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Function/tastypie.http:HttpApplicationError.close', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
]

if DJANGO_VERSION < (1, 10):
    _test_application_raises_zerodivision.append(
            ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 1))
else:
    _test_application_raises_zerodivision.append(
            ('Function/django.urls.resolvers:RegexURLResolver.resolve', 1))

if six.PY3:
    _test_application_raises_zerodivision.append(
        ('Function/tastypie.resources:Resource.wrap_view.<locals>.wrapper', 1))
else:
    _test_application_raises_zerodivision.append(
            ('Function/tastypie.resources:wrapper', 1))

_test_application_raises_zerodivision_exceptions = []
if six.PY3:
    _test_application_raises_zerodivision_exceptions.append(
            'builtins:ZeroDivisionError')
else:
    _test_application_raises_zerodivision_exceptions.append(
            'exceptions:ZeroDivisionError')


@pytest.mark.parametrize('api_version', ['v1', 'v2'])
@validate_transaction_errors(
        errors=_test_application_raises_zerodivision_exceptions)
@validate_transaction_metrics('api:SimpleResource.dispatch_detail',
        scoped_metrics=_test_application_raises_zerodivision)
def test_raises_zerodivision(api_version):
    test_application.get('/api/%s/simple/ZeroDivisionError/' % api_version,
            status=500)


@pytest.mark.parametrize('api_version', ['v1', 'v2'])
@override_ignore_status_codes(set())  # don't ignore any status codes
@validate_transaction_errors(errors=['tastypie.exceptions:NotFound'])
@validate_transaction_metrics('api:SimpleResource.dispatch_detail',
        scoped_metrics=_test_application_not_found_scoped_metrics)
def test_record_404_errors(api_version):
    test_application.get('/api/%s/simple/NotFound/' % api_version, status=404)
