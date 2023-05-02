# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pytest
import django

from newrelic.core.config import global_settings
from newrelic.common.encoding_utils import gzip_decompress
from testing_support.fixtures import (
    override_application_settings,
    override_generic_settings, override_ignore_status_codes)
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors

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

rollup_metrics = scoped_metrics + [
    ('Python/Framework/Django/%s' % django.get_version(), 1),
]


@pytest.fixture
def application():
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    return AsgiTest(get_asgi_application())


@validate_transaction_metrics('views:index',
        scoped_metrics=[('Function/views:index', 1)] + scoped_metrics,
        rollup_metrics=rollup_metrics)
@validate_code_level_metrics("views", "index")
def test_asgi_index(application):
    response = application.get('/')
    assert response.status == 200


@validate_transaction_metrics('views:exception',
        scoped_metrics=[('Function/views:exception', 1)] + scoped_metrics,
        rollup_metrics=rollup_metrics)
@validate_code_level_metrics("views", "exception")
def test_asgi_exception(application):
    response = application.get('/exception')
    assert response.status == 500


@override_ignore_status_codes([410])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:middleware_410',
        scoped_metrics=[('Function/views:middleware_410', 1)] + scoped_metrics,
        rollup_metrics=rollup_metrics)
@validate_code_level_metrics("views", "middleware_410")
def test_asgi_middleware_ignore_status_codes(application):
    response = application.get('/middleware_410')
    assert response.status == 410


@override_ignore_status_codes([403])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:permission_denied',
        scoped_metrics=[('Function/views:permission_denied', 1)] + scoped_metrics,
        rollup_metrics=rollup_metrics)
@validate_code_level_metrics("views", "permission_denied")
def test_asgi_ignored_status_code(application):
    response = application.get('/permission_denied')
    assert response.status == 403


@pytest.mark.parametrize('url,view_name', (
    ('/cbv', 'views:MyView.get'),
    ('/deferred_cbv', 'views:deferred_cbv'),
))
def test_asgi_class_based_view(application, url, view_name):
    func = 'get' if url == '/cbv' else 'deferred_cbv'
    namespace = 'views.MyView' if func == 'get' else 'views'
   
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(view_name,
            scoped_metrics=[('Function/' + view_name, 1)] + scoped_metrics,
            rollup_metrics=rollup_metrics)
    @validate_code_level_metrics(namespace, func)
    def _test():
        response = application.get(url)
        assert response.status == 200

    _test()


@pytest.mark.parametrize('url', (
    '/html_insertion',
    '/html_insertion_content_length',
    '/template_tags',
    '/gzip_html_insertion',
))
@override_application_settings({
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
})
def test_asgi_html_insertion_success(application, url):
    if 'gzip' in url:
        headers = {'Accept-Encoding': 'gzip'}
    else:
        headers = None
    response = application.get(url, headers=headers)
    assert response.status == 200

    if 'gzip' in url:
        body = gzip_decompress(response.body).encode('utf-8')
    else:
        body = response.body

    assert b'NREUM HEADER' in body
    assert b'NREUM.info' in body
    assert b'&lt;!-- NREUM HEADER --&gt' not in body


@pytest.mark.parametrize('url', (
    '/html_insertion_manual',
    '/html_insertion_unnamed_attachment_header',
    '/html_insertion_named_attachment_header',
))
@override_application_settings({
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
})
def test_asgi_html_insertion_failed(application, url):
    response = application.get(url)
    assert response.status == 200

    assert b'NREUM HEADER' not in response.body
    assert b'NREUM.info' not in response.body


@validate_transaction_metrics('views:template_tags',
        scoped_metrics=[
                ('Function/views:template_tags', 1),
                ('Template/Render/main.html', 1),
                ('Template/Render/results.html', 1)] + scoped_metrics,
        rollup_metrics=rollup_metrics)
@validate_code_level_metrics('views', 'template_tags')
def test_asgi_template_render(application):
    response = application.get('/template_tags')
    assert response.status == 200


@override_generic_settings(global_settings(), {'enabled': False})
def test_asgi_nr_disabled(application):
    response = application.get('/')
    assert response.status == 200
