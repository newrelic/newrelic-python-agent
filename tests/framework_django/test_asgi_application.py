import os
import pytest
import django

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_application_settings,
    override_generic_settings, override_ignore_status_codes)

DJANGO_VERSION = tuple(map(int, django.get_version().split('.')[:2]))

if DJANGO_VERSION[0] < 3:
    pytest.skip("support for asgi added in django 3", allow_module_level=True)

from testing_support.asgi_testing import AsgiTest


scoped_metrics = [
    ('Function/django.contrib.sessions.middleware:SessionMiddleware', 1),
    ('Function/django.middleware.common:CommonMiddleware', 1),
    ('Function/django.middleware.csrf:CsrfViewMiddleware', 1),
    ('Function/django.contrib.auth.middleware:AuthenticationMiddleware', 1),
    ('Function/django.contrib.messages.middleware:MessageMiddleware', 1),
    ('Function/django.middleware.gzip:GZipMiddleware', 1),
    ('Function/middleware:ExceptionTo410Middleware', 1),
    ('Function/django.urls.resolvers:URLResolver.resolve', 'present'),
]


@pytest.fixture(scope="module")
def application():
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    return AsgiTest(get_asgi_application())


@validate_transaction_metrics('views:index',
        scoped_metrics=[('Function/views:index', 1)] + scoped_metrics)
def test_asgi_index(application):
    response = application.get('/')
    assert response.status == 200


@validate_transaction_metrics('views:exception',
        scoped_metrics=[('Function/views:exception', 1)] + scoped_metrics)
def test_asgi_exception(application):
    response = application.get('/exception')
    assert response.status == 500


@override_ignore_status_codes([410])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:middleware_410',
        scoped_metrics=[('Function/views:middleware_410', 1)] + scoped_metrics)
def test_asgi_middleware_ignore_status_codes(application):
    response = application.get('/middleware_410')
    assert response.status == 410


@override_ignore_status_codes([403])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:permission_denied',
        scoped_metrics=[('Function/views:permission_denied', 1)] + scoped_metrics)
def test_asgi_ignored_status_code(application):
    response = application.get('/permission_denied')
    assert response.status == 403


@pytest.mark.parametrize('url,view_name', (
    ('/cbv', 'views:MyView.get'),
    ('/deferred_cbv', 'views:deferred_cbv'),
))
def test_asgi_class_based_view(application, url, view_name):

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(view_name,
            scoped_metrics=[('Function/' + view_name, 1)] + scoped_metrics)
    def _test():
        response = application.get(url)
        assert response.status == 200

    _test()


@pytest.mark.parametrize('url', (
    '/html_insertion',
    '/html_insertion_content_length',
))
@override_application_settings({
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
})
def test_asgi_html_insertion_success(application, url):
    response = application.get(url)
    assert response.status == 200

    assert b'NREUM HEADER' in response.body
    assert b'NREUM.info' in response.body
