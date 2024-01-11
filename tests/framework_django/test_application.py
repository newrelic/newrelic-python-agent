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

from testing_support.fixtures import (
    override_application_settings,
    override_generic_settings, override_ignore_status_codes)
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from newrelic.hooks.framework_django import django_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors

import os

import django

DJANGO_VERSION = tuple(map(int, django.get_version().split('.')[:2]))
DJANGO_SETTINGS_MODULE = os.environ.get('DJANGO_SETTINGS_MODULE', None)


def target_application():
    from _target_application import _target_application
    return _target_application


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
    ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
    ('Python/WSGI/Application', 1),
    ('Python/WSGI/Response', 1),
    ('Python/WSGI/Finalize', 1),
    ('Function/views:index', 1),
]

if DJANGO_VERSION >= (1, 5):
    _test_application_index_scoped_metrics.extend([
            ('Function/django.http.response:HttpResponse.close', 1)])

if DJANGO_VERSION < (1, 10):
    _test_application_index_scoped_metrics.extend(
        _test_django_pre_1_10_url_resolver_scoped_metrics)
elif DJANGO_VERSION >= (2, 0):
    _test_application_index_scoped_metrics.extend(
        _test_django_post_2_0_url_resolver_scoped_metrics)
else:
    _test_application_index_scoped_metrics.extend(
        _test_django_post_1_10_url_resolver_scoped_metrics)

if DJANGO_SETTINGS_MODULE == 'settings_0110_old':
    _test_application_index_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)
elif DJANGO_SETTINGS_MODULE == 'settings_0110_new':
    _test_application_index_scoped_metrics.extend(
        _test_django_post_1_10_middleware_scoped_metrics)
elif DJANGO_VERSION < (1, 10):
    _test_application_index_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:index',
        scoped_metrics=_test_application_index_scoped_metrics)
@validate_code_level_metrics("views", "index")
def test_application_index():
    test_application = target_application()
    response = test_application.get('')
    response.mustcontain('INDEX RESPONSE')


@validate_transaction_metrics('views:exception')
@validate_code_level_metrics("views", "exception")
def test_application_exception():
    test_application = target_application()
    test_application.get('/exception', status=500)


_test_application_not_found_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
]

if DJANGO_VERSION >= (1, 5):
    _test_application_not_found_scoped_metrics.extend([
            ('Function/django.http.response:HttpResponseNotFound.close', 1)])

if DJANGO_VERSION < (1, 10):
    _test_application_not_found_scoped_metrics.extend(
        _test_django_pre_1_10_url_resolver_scoped_metrics)
elif DJANGO_VERSION >= (2, 0):
    _test_application_not_found_scoped_metrics.extend(
        _test_django_post_2_0_url_resolver_scoped_metrics)
else:
    _test_application_not_found_scoped_metrics.extend(
        _test_django_post_1_10_url_resolver_scoped_metrics)

if DJANGO_SETTINGS_MODULE == 'settings_0110_old':
    _test_application_not_found_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)
    # The `CsrfViewMiddleware.process_view` isn't called for 404 Not Found.
    _test_application_not_found_scoped_metrics.remove(
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_view', 1))
elif DJANGO_SETTINGS_MODULE == 'settings_0110_new':
    _test_application_not_found_scoped_metrics.extend(
        _test_django_post_1_10_middleware_scoped_metrics)
elif DJANGO_VERSION < (1, 10):
    _test_application_not_found_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)
    # The `CsrfViewMiddleware.process_view` isn't called for 404 Not Found.
    _test_application_not_found_scoped_metrics.remove(
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_view', 1))


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('django.views.debug:technical_404_response',
        scoped_metrics=_test_application_not_found_scoped_metrics)
def test_application_not_found():
    test_application = target_application()
    test_application.get('/not_found', status=404)


@override_ignore_status_codes([403])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:permission_denied')
@validate_code_level_metrics("views", "permission_denied")
def test_ignored_status_code():
    test_application = target_application()
    test_application.get('/permission_denied', status=403)


@override_ignore_status_codes([410])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:middleware_410')
@validate_code_level_metrics("views", "middleware_410")
def test_middleware_ignore_status_codes():
    test_application = target_application()
    test_application.get('/middleware_410', status=410)


_test_application_cbv_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:MyView', 1),
        ('Function/views:MyView.get', 1),
]

if DJANGO_VERSION >= (1, 5):
    _test_application_cbv_scoped_metrics.extend([
            ('Function/django.http.response:HttpResponse.close', 1)])

if DJANGO_VERSION < (1, 10):
    _test_application_cbv_scoped_metrics.extend(
        _test_django_pre_1_10_url_resolver_scoped_metrics)
elif DJANGO_VERSION >= (2, 0):
    _test_application_cbv_scoped_metrics.extend(
        _test_django_post_2_0_url_resolver_scoped_metrics)
else:
    _test_application_cbv_scoped_metrics.extend(
        _test_django_post_1_10_url_resolver_scoped_metrics)

if DJANGO_SETTINGS_MODULE == 'settings_0110_old':
    _test_application_cbv_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)
elif DJANGO_SETTINGS_MODULE == 'settings_0110_new':
    _test_application_cbv_scoped_metrics.extend(
        _test_django_post_1_10_middleware_scoped_metrics)
elif DJANGO_VERSION < (1, 10):
    _test_application_cbv_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:MyView.get',
        scoped_metrics=_test_application_cbv_scoped_metrics)
@validate_code_level_metrics("views.MyView", "get")
def test_application_cbv():
    test_application = target_application()
    response = test_application.get('/cbv')
    response.mustcontain('CBV RESPONSE')


_test_application_deferred_cbv_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:deferred_cbv', 1),
        ('Function/views:MyView.get', 1),
]

if DJANGO_VERSION >= (1, 5):
    _test_application_deferred_cbv_scoped_metrics.extend([
            ('Function/django.http.response:HttpResponse.close', 1)])

if DJANGO_VERSION < (1, 10):
    _test_application_deferred_cbv_scoped_metrics.extend(
        _test_django_pre_1_10_url_resolver_scoped_metrics)
elif DJANGO_VERSION >= (2, 0):
    _test_application_deferred_cbv_scoped_metrics.extend(
        _test_django_post_2_0_url_resolver_scoped_metrics)
else:
    _test_application_deferred_cbv_scoped_metrics.extend(
        _test_django_post_1_10_url_resolver_scoped_metrics)

if DJANGO_SETTINGS_MODULE == 'settings_0110_old':
    _test_application_deferred_cbv_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)
elif DJANGO_SETTINGS_MODULE == 'settings_0110_new':
    _test_application_deferred_cbv_scoped_metrics.extend(
        _test_django_post_1_10_middleware_scoped_metrics)
elif DJANGO_VERSION < (1, 10):
    _test_application_deferred_cbv_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:deferred_cbv',
        scoped_metrics=_test_application_deferred_cbv_scoped_metrics)
@validate_code_level_metrics("views", "deferred_cbv")
def test_application_deferred_cbv():
    test_application = target_application()
    response = test_application.get('/deferred_cbv')
    response.mustcontain('CBV RESPONSE')


_test_html_insertion_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}


@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_django_middleware():
    test_application = target_application()
    response = test_application.get('/html_insertion', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain('NREUM HEADER', 'NREUM.info')


@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_django_gzip_middleware_enabled():
    test_application = target_application()

    # GZipMiddleware only fires if given the following header.

    gzip_header = {'Accept-Encoding': 'gzip'}
    response = test_application.get('/gzip_html_insertion', status=200,
            headers=gzip_header)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    # The response.text will already be gunzipped

    response.mustcontain('NREUM HEADER', 'NREUM.info')


_test_html_insertion_settings_disabled = {
    'browser_monitoring.enabled': False,
    'browser_monitoring.auto_instrument': False,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}


@override_application_settings(_test_html_insertion_settings_disabled)
def test_html_insertion_django_gzip_middleware_disabled():
    test_application = target_application()

    # GZipMiddleware only fires if given the following header.

    gzip_header = {'Accept-Encoding': 'gzip'}
    response = test_application.get('/gzip_html_insertion', status=200,
            headers=gzip_header)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    # The response.text will already be gunzipped

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])


_test_html_insertion_manual_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}


@override_application_settings(_test_html_insertion_manual_settings)
def test_html_insertion_manual_django_middleware():
    test_application = target_application()
    response = test_application.get('/html_insertion_manual', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])


@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_unnamed_attachment_header_django_middleware():
    test_application = target_application()
    response = test_application.get(
            '/html_insertion_unnamed_attachment_header', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])


@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_named_attachment_header_django_middleware():
    test_application = target_application()
    response = test_application.get(
            '/html_insertion_named_attachment_header', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])


_test_html_insertion_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': False,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}


@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_manual_tag_instrumentation():
    test_application = target_application()
    response = test_application.get('/template_tags')

    # Assert that the instrumentation is not inappropriately escaped

    response.mustcontain('<!-- NREUM HEADER -->',
            no=['&lt;!-- NREUM HEADER --&gt'])


_test_application_inclusion_tag_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:inclusion_tag', 1),
        ('Template/Render/main.html', 1),
]

if DJANGO_VERSION < (1, 9):
    _test_application_inclusion_tag_scoped_metrics.extend([
            ('Template/Include/results.html', 1)])

if DJANGO_VERSION < (1, 10):
    _test_application_inclusion_tag_scoped_metrics.extend(
        _test_django_pre_1_10_url_resolver_scoped_metrics)
elif DJANGO_VERSION >= (2, 0):
    _test_application_inclusion_tag_scoped_metrics.extend(
        _test_django_post_2_0_url_resolver_scoped_metrics)
else:
    _test_application_inclusion_tag_scoped_metrics.extend(
        _test_django_post_1_10_url_resolver_scoped_metrics)

if DJANGO_SETTINGS_MODULE == 'settings_0110_old':
    _test_application_inclusion_tag_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)
elif DJANGO_SETTINGS_MODULE == 'settings_0110_new':
    _test_application_inclusion_tag_scoped_metrics.extend(
        _test_django_post_1_10_middleware_scoped_metrics)
elif DJANGO_VERSION < (1, 10):
    _test_application_inclusion_tag_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)

try:
    _test_application_inclusion_tag_scoped_metrics.remove(
        (('Function/newrelic.hooks.framework_django:'
                'browser_timing_insertion'), 1)
    )
except ValueError:
    pass


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:inclusion_tag',
        scoped_metrics=_test_application_inclusion_tag_scoped_metrics)
@validate_code_level_metrics("views", "inclusion_tag")
def test_application_inclusion_tag():
    test_application = target_application()
    response = test_application.get('/inclusion_tag')
    response.mustcontain('Inclusion tag')


_test_inclusion_tag_template_tags_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:inclusion_tag', 1),
        ('Template/Render/main.html', 1),
]

if DJANGO_VERSION < (1, 9):
    _test_inclusion_tag_template_tags_scoped_metrics.extend([
        ('Template/Include/results.html', 1),
        ('Template/Tag/show_results', 1)])

_test_inclusion_tag_settings = {
    'instrumentation.templates.inclusion_tag': '*'
}

if DJANGO_VERSION < (1, 10):
    _test_inclusion_tag_template_tags_scoped_metrics.extend(
        _test_django_pre_1_10_url_resolver_scoped_metrics)
elif DJANGO_VERSION >= (2, 0):
    _test_inclusion_tag_template_tags_scoped_metrics.extend(
        _test_django_post_2_0_url_resolver_scoped_metrics)
else:
    _test_inclusion_tag_template_tags_scoped_metrics.extend(
        _test_django_post_1_10_url_resolver_scoped_metrics)

if DJANGO_SETTINGS_MODULE == 'settings_0110_old':
    _test_inclusion_tag_template_tags_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)
elif DJANGO_SETTINGS_MODULE == 'settings_0110_new':
    _test_inclusion_tag_template_tags_scoped_metrics.extend(
        _test_django_post_1_10_middleware_scoped_metrics)
elif DJANGO_VERSION < (1, 10):
    _test_inclusion_tag_template_tags_scoped_metrics.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)

try:
    _test_inclusion_tag_template_tags_scoped_metrics.remove(
        (('Function/newrelic.hooks.framework_django:'
                'browser_timing_insertion'), 1)
    )
except ValueError:
    pass


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:inclusion_tag',
        scoped_metrics=_test_inclusion_tag_template_tags_scoped_metrics)
@override_generic_settings(django_settings, _test_inclusion_tag_settings)
@validate_code_level_metrics("views", "inclusion_tag")
def test_inclusion_tag_template_tag_metric():
    test_application = target_application()
    response = test_application.get('/inclusion_tag')
    response.mustcontain('Inclusion tag')


_test_template_render_exception_scoped_metrics_base = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
]

if DJANGO_VERSION < (1, 5):
    _test_template_render_exception_scoped_metrics_base.append(
            ('Function/django.http:HttpResponseServerError.close', 1))
elif DJANGO_VERSION < (1, 8):
    _test_template_render_exception_scoped_metrics_base.append(
            ('Function/django.http.response:HttpResponseServerError.close', 1))
else:
    _test_template_render_exception_scoped_metrics_base.append(
            ('Function/django.http.response:HttpResponse.close', 1))

if DJANGO_VERSION < (1, 10):
    _test_template_render_exception_scoped_metrics_base.extend(
        _test_django_pre_1_10_url_resolver_scoped_metrics)
elif DJANGO_VERSION >= (2, 0):
    _test_template_render_exception_scoped_metrics_base.extend(
        _test_django_post_2_0_url_resolver_scoped_metrics)
else:
    _test_template_render_exception_scoped_metrics_base.extend(
        _test_django_post_1_10_url_resolver_scoped_metrics)

if DJANGO_SETTINGS_MODULE == 'settings_0110_old':
    _test_template_render_exception_scoped_metrics_base.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)
elif DJANGO_SETTINGS_MODULE == 'settings_0110_new':
    _test_template_render_exception_scoped_metrics_base.extend(
        _test_django_post_1_10_middleware_scoped_metrics)
elif DJANGO_VERSION < (1, 10):
    _test_template_render_exception_scoped_metrics_base.extend(
        _test_django_pre_1_10_middleware_scoped_metrics)

if DJANGO_VERSION < (1, 9):
    _test_template_render_exception_errors = [
        'django.template.base:TemplateSyntaxError']
else:
    _test_template_render_exception_errors = [
        'django.template.exceptions:TemplateSyntaxError']

_test_template_render_exception_function_scoped_metrics = list(
        _test_template_render_exception_scoped_metrics_base)
_test_template_render_exception_function_scoped_metrics.extend([
        ('Function/views:render_exception_function', 1),
])


@validate_transaction_errors(errors=_test_template_render_exception_errors)
@validate_transaction_metrics('views:render_exception_function',
        scoped_metrics=_test_template_render_exception_function_scoped_metrics)
@validate_code_level_metrics("views", "render_exception_function")
def test_template_render_exception_function():
    test_application = target_application()
    test_application.get('/render_exception_function', status=500)


_test_template_render_exception_class_scoped_metrics = list(
        _test_template_render_exception_scoped_metrics_base)
_test_template_render_exception_class_scoped_metrics.extend([
        ('Function/views:RenderExceptionClass', 1),
        ('Function/views:RenderExceptionClass.get', 1),
])


@validate_transaction_errors(errors=_test_template_render_exception_errors)
@validate_transaction_metrics('views:RenderExceptionClass.get',
        scoped_metrics=_test_template_render_exception_class_scoped_metrics)
@validate_code_level_metrics("views.RenderExceptionClass", "get")
def test_template_render_exception_class():
    test_application = target_application()
    test_application.get('/render_exception_class', status=500)
