import webtest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_application_settings,
    override_generic_settings)

from wsgi import application

from newrelic.packages import six
from newrelic.agent import application_settings
from newrelic.hooks.framework_django import django_settings

import json

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

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:index',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index():
    response = test_application.get('')
    response.mustcontain('INDEX RESPONSE')

    assert 'Content-Length' not in response.headers

@validate_transaction_metrics('views:exception')
def test_application_exception():
    response = test_application.get('/exception', status=500)

_test_application_not_found_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_request', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_request', 1),
        ('Function/django.contrib.auth.middleware:AuthenticationMiddleware.process_request', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_request', 1),
        #('Function/django.core.urlresolvers:RegexURLResolver.resolve', 3),
        #('Function/django.core.urlresolvers:RegexURLResolver.resolve_error_handler', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_response', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_response', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_response', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_response', 1),
        ('Function/newrelic.hooks.framework_django:browser_timing_middleware', 1)]

if DJANGO_VERSION >= (1, 5):
    if six.PY3:
        _test_application_not_found_scoped_metrics.extend([
                ('Function/django.http.response:HttpResponseBase.close', 1)])
    else:
        _test_application_not_found_scoped_metrics.extend([
                ('Function/django.http.response:HttpResponseNotFound.close', 1)])

if DJANGO_VERSION >= (1, 8):
    _test_application_not_found_scoped_metrics.extend([
            ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 4)])
else:
    _test_application_not_found_scoped_metrics.extend([
            ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 3)])

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('django.views.debug:technical_404_response',
        scoped_metrics=_test_application_not_found_scoped_metrics)
def test_application_not_found():
    response = test_application.get('/not_found', status=404)

_test_application_cbv_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:MyView', 1),
        ('Function/views:MyView.get', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_request', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_request', 1),
        ('Function/django.contrib.auth.middleware:AuthenticationMiddleware.process_request', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_request', 1),
        ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 2),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_view', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_response', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_response', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_response', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_response', 1),
        ('Function/newrelic.hooks.framework_django:browser_timing_middleware', 1)]

if DJANGO_VERSION >= (1, 5):
    if six.PY3:
        _test_application_cbv_scoped_metrics.extend([
                ('Function/django.http.response:HttpResponseBase.close', 1)])
    else:
        _test_application_cbv_scoped_metrics.extend([
                ('Function/django.http.response:HttpResponse.close', 1)])

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:MyView.get',
        scoped_metrics=_test_application_cbv_scoped_metrics)
def test_application_cbv():
    response = test_application.get('/cbv')
    response.mustcontain('CBV RESPONSE')

_test_application_deferred_cbv_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:deferred_cbv', 1),
        ('Function/views:MyView.get', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_request', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_request', 1),
        ('Function/django.contrib.auth.middleware:AuthenticationMiddleware.process_request', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_request', 1),
        ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 2),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_view', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_response', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_response', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_response', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_response', 1),
        ('Function/newrelic.hooks.framework_django:browser_timing_middleware', 1)]

if DJANGO_VERSION >= (1, 5):
    if six.PY3:
        _test_application_deferred_cbv_scoped_metrics.extend([
                ('Function/django.http.response:HttpResponseBase.close', 1)])
    else:
        _test_application_deferred_cbv_scoped_metrics.extend([
                ('Function/django.http.response:HttpResponse.close', 1)])

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:deferred_cbv',
        scoped_metrics=_test_application_deferred_cbv_scoped_metrics)
def test_application_deferred_cbv():
    response = test_application.get('/deferred_cbv')
    response.mustcontain('CBV RESPONSE')

_test_html_insertion_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_django_middleware():
    response = test_application.get('/html_insertion', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain('NREUM HEADER', 'NREUM.info')

_test_html_insertion_manual_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_html_insertion_manual_settings)
def test_html_insertion_manual_django_middleware():
    response = test_application.get('/html_insertion_manual', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])

@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_unnamed_attachment_header_django_middleware():
    response = test_application.get(
            '/html_insertion_unnamed_attachment_header', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])

@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_named_attachment_header_django_middleware():
    response = test_application.get(
            '/html_insertion_named_attachment_header', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])

@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_no_content_length_header():
    response = test_application.get('/html_insertion')

    assert 'Content-Length' not in response.headers

@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_content_length_header():
    response = test_application.get('/html_insertion_content_length')

    assert 'Content-Length' in response.headers

_test_application_inclusion_tag_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:inclusion_tag', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_request', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_request', 1),
        ('Function/django.contrib.auth.middleware:AuthenticationMiddleware.process_request', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_request', 1),
        ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 2),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_view', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_response', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_response', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_response', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_response', 1),
        ('Function/newrelic.hooks.framework_django:browser_timing_middleware', 1),
        ('Template/Render/main.html', 1),
        ('Template/Include/results.html', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:inclusion_tag',
        scoped_metrics=_test_application_inclusion_tag_scoped_metrics)
def test_application_inclusion_tag():
    response = test_application.get('/inclusion_tag')
    response.mustcontain('Inclusion tag')

_test_inclusion_tag_template_tags_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/views:inclusion_tag', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_request', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_request', 1),
        ('Function/django.contrib.auth.middleware:AuthenticationMiddleware.process_request', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_request', 1),
        ('Function/django.core.urlresolvers:RegexURLResolver.resolve', 2),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_view', 1),
        ('Function/django.contrib.messages.middleware:MessageMiddleware.process_response', 1),
        ('Function/django.middleware.csrf:CsrfViewMiddleware.process_response', 1),
        ('Function/django.contrib.sessions.middleware:SessionMiddleware.process_response', 1),
        ('Function/django.middleware.common:CommonMiddleware.process_response', 1),
        ('Function/newrelic.hooks.framework_django:browser_timing_middleware', 1),
        ('Template/Render/main.html', 1),
        ('Template/Include/results.html', 1),
        ('Template/Tag/show_results', 1)]

_test_inclusion_tag_settings = {
    'instrumentation.templates.inclusion_tag': '*'
}

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:inclusion_tag',
        scoped_metrics=_test_inclusion_tag_template_tags_scoped_metrics)
@override_generic_settings(django_settings, _test_inclusion_tag_settings)
def test_inclusion_tag_template_tag_metric():
    response = test_application.get('/inclusion_tag')
    response.mustcontain('Inclusion tag')
