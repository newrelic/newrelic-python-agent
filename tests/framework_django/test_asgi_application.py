import os
import pytest
import django

from testing_support.asgi_testing import AsgiTest
from testing_support.fixtures import validate_transaction_metrics

DJANGO_VERSION = tuple(map(int, django.get_version().split('.')[:2]))


# The middleware scoped metrics are dependent on the MIDDLEWARE_CLASSES or
# MIDDLEWARE defined in the version-specific Django settings.py file.

_test_django_pre_1_10_middleware_scoped_metrics = [
    (('Function/django.middleware.common:'
            'CommonMiddleware.process_request'), 1),
    (('Function/django.contrib.sessions.middleware:'
            'SessionMiddleware.process_request'), 1),
    (('Function/django.contrib.auth.middleware:'
            'AuthenticationMiddleware.process_request'), 1),
    (('Function/django.contrib.messages.middleware:'
            'MessageMiddleware.process_request'), 1),
    (('Function/django.middleware.csrf:'
            'CsrfViewMiddleware.process_view'), 1),
    (('Function/django.contrib.messages.middleware:'
            'MessageMiddleware.process_response'), 1),
    (('Function/django.middleware.csrf:'
            'CsrfViewMiddleware.process_response'), 1),
    (('Function/django.contrib.sessions.middleware:'
            'SessionMiddleware.process_response'), 1),
    (('Function/django.middleware.common:'
            'CommonMiddleware.process_response'), 1),
    (('Function/django.middleware.gzip:'
            'GZipMiddleware.process_response'), 1),
    (('Function/newrelic.hooks.framework_django:'
            'browser_timing_insertion'), 1),
]

_test_django_post_1_10_middleware_scoped_metrics = [
    ('Function/django.middleware.security:SecurityMiddleware', 1),
    ('Function/django.contrib.sessions.middleware:SessionMiddleware', 1),
    ('Function/django.middleware.common:CommonMiddleware', 1),
    ('Function/django.middleware.csrf:CsrfViewMiddleware', 1),
    ('Function/django.contrib.auth.middleware:AuthenticationMiddleware', 1),
    ('Function/django.contrib.messages.middleware:MessageMiddleware', 1),
    ('Function/django.middleware.clickjacking:XFrameOptionsMiddleware', 1),
    ('Function/django.middleware.gzip:GZipMiddleware', 1),
]

_test_django_pre_1_10_url_resolver_scoped_metrics = [
    ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 'present'),
]

_test_django_post_1_10_url_resolver_scoped_metrics = [
    ('Function/django.urls.resolvers:RegexURLResolver.resolve', 'present'),
]

_test_django_post_2_0_url_resolver_scoped_metrics = [
    ('Function/django.urls.resolvers:URLResolver.resolve', 'present'),
]

_test_application_index_scoped_metrics = [
    ('Function/views:index', 1),
]

if DJANGO_VERSION < (1, 10):
    _test_application_index_scoped_metrics.extend(
        _test_django_pre_1_10_url_resolver_scoped_metrics)
elif DJANGO_VERSION >= (2, 0):
    _test_application_index_scoped_metrics.extend(
        _test_django_post_2_0_url_resolver_scoped_metrics)
else:
    _test_application_index_scoped_metrics.extend(
        _test_django_post_1_10_url_resolver_scoped_metrics)

if DJANGO_VERSION < (1, 10):
    _test_application_index_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)


@pytest.fixture(scope="module")
def application():
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    return AsgiTest(get_asgi_application())


@validate_transaction_metrics('views:index',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_asgi_index(application):
    response = application.get('/')
    assert response.status == 200
