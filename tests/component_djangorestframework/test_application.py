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

import pytest
import webtest

from newrelic.packages import six
from newrelic.core.config import global_settings

from testing_support.fixtures import (
    override_generic_settings,
    function_not_called)
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
import django

DJANGO_VERSION = tuple(map(int, django.get_version().split('.')[:2]))


@pytest.fixture(scope='module')
def target_application():
    from wsgi import application
    test_application = webtest.TestApp(application)
    return test_application


if DJANGO_VERSION >= (1, 10):
    url_module_path = 'django.urls.resolvers'

    # Django 1.10 new style middleware removed individual process_* methods.
    # All middleware in Django 1.10+ is called through the __call__ methods on
    # middlwares.
    process_request_method = ''
    process_view_method = ''
    process_response_method = ''
else:
    url_module_path = 'django.core.urlresolvers'
    process_request_method = '.process_request'
    process_view_method = '.process_view'
    process_response_method = '.process_response'

if DJANGO_VERSION >= (2, 0):
    url_resolver_cls = 'URLResolver'
else:
    url_resolver_cls = 'RegexURLResolver'

_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        (('Function/django.middleware.common:'
                'CommonMiddleware' + process_request_method), 1),
        (('Function/django.contrib.sessions.middleware:'
                'SessionMiddleware' + process_request_method), 1),
        (('Function/django.contrib.auth.middleware:'
                'AuthenticationMiddleware' + process_request_method), 1),
        (('Function/django.contrib.messages.middleware:'
                'MessageMiddleware' + process_request_method), 1),
        (('Function/%s:' % url_module_path +
                '%s.resolve' % url_resolver_cls), 1),
        (('Function/django.middleware.csrf:'
                'CsrfViewMiddleware' + process_view_method), 1),
        (('Function/django.contrib.messages.middleware:'
                'MessageMiddleware' + process_response_method), 1),
        (('Function/django.middleware.csrf:'
                'CsrfViewMiddleware' + process_response_method), 1),
        (('Function/django.contrib.sessions.middleware:'
                'SessionMiddleware' + process_response_method), 1),
        (('Function/django.middleware.common:'
                'CommonMiddleware' + process_response_method), 1),
]

_test_application_index_scoped_metrics = list(_scoped_metrics)
_test_application_index_scoped_metrics.append(('Function/views:index', 1))

if DJANGO_VERSION >= (1, 5):
    _test_application_index_scoped_metrics.extend([
            ('Function/django.http.response:HttpResponse.close', 1)])


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:index',
        scoped_metrics=_test_application_index_scoped_metrics)
@validate_code_level_metrics("views", "index")
def test_application_index(target_application):
    response = target_application.get('')
    response.mustcontain('INDEX RESPONSE')


_test_application_view_scoped_metrics = list(_scoped_metrics)
_test_application_view_scoped_metrics.append(('Function/urls:View.get', 1))

if DJANGO_VERSION >= (1, 5):
    _test_application_view_scoped_metrics.extend([
            ('Function/rest_framework.response:Response.close', 1)])


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('urls:View.get',
    scoped_metrics=_test_application_view_scoped_metrics)
@validate_code_level_metrics("urls.View", "get")
def test_application_view(target_application):
    response = target_application.get('/view/')
    assert response.status_int == 200
    response.mustcontain('restframework view response')


_test_application_view_error_scoped_metrics = list(_scoped_metrics)
_test_application_view_error_scoped_metrics.append(
        ('Function/urls:ViewError.get', 1))


@validate_transaction_errors(errors=['urls:Error'])
@validate_transaction_metrics('urls:ViewError.get',
    scoped_metrics=_test_application_view_error_scoped_metrics)
@validate_code_level_metrics("urls.ViewError", "get")
def test_application_view_error(target_application):
    target_application.get('/view_error/', status=500)


_test_application_view_handle_error_scoped_metrics = list(_scoped_metrics)
_test_application_view_handle_error_scoped_metrics.append(
        ('Function/urls:ViewHandleError.get', 1))


@pytest.mark.parametrize('status,should_record', [(418, True), (200, False)])
@pytest.mark.parametrize('use_global_exc_handler', [True, False])
@validate_code_level_metrics("urls.ViewHandleError", "get")
def test_application_view_handle_error(status, should_record,
        use_global_exc_handler, target_application):
    errors = ['urls:Error'] if should_record else []

    @validate_transaction_errors(errors=errors)
    @validate_transaction_metrics('urls:ViewHandleError.get',
        scoped_metrics=_test_application_view_handle_error_scoped_metrics)
    def _test():
        response = target_application.get(
                '/view_handle_error/%s/%s/' % (status, use_global_exc_handler),
                status=status)
        if use_global_exc_handler:
            response.mustcontain('exception was handled global')
        else:
            response.mustcontain('exception was handled not global')

    _test()


_test_api_view_view_name_get = 'urls:wrapped_view.get'
_test_api_view_scoped_metrics_get = list(_scoped_metrics)
_test_api_view_scoped_metrics_get.append(
        ('Function/%s' % _test_api_view_view_name_get, 1))


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(_test_api_view_view_name_get,
    scoped_metrics=_test_api_view_scoped_metrics_get)
@validate_code_level_metrics("urls.WrappedAPIView" if six.PY3 else "urls", "wrapped_view")
def test_api_view_get(target_application):
    response = target_application.get('/api_view/')
    response.mustcontain('wrapped_view response')


_test_api_view_view_name_post = 'urls:wrapped_view.http_method_not_allowed'
_test_api_view_scoped_metrics_post = list(_scoped_metrics)
_test_api_view_scoped_metrics_post.append(
        ('Function/%s' % _test_api_view_view_name_post, 1))


@validate_transaction_errors(
        errors=['rest_framework.exceptions:MethodNotAllowed'])
@validate_transaction_metrics(_test_api_view_view_name_post,
    scoped_metrics=_test_api_view_scoped_metrics_post)
def test_api_view_method_not_allowed(target_application):
    target_application.post('/api_view/', status=405)


def test_application_view_agent_disabled(target_application):
    settings = global_settings()

    @override_generic_settings(settings, {'enabled': False})
    @function_not_called('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _test():
        response = target_application.get('/view/')
        assert response.status_int == 200
        response.mustcontain('restframework view response')

    _test()
