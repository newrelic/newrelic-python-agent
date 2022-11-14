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
import six
import webtest

from tastypie import VERSION

from newrelic.api.background_task import background_task
from newrelic.api.transaction import end_of_transaction

from testing_support.fixtures import override_ignore_status_codes
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics

from wsgi import application

test_application = webtest.TestApp(application)

_test_application_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Function/django.http.response:HttpResponse.close', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
]

_test_application_index_scoped_metrics = list(_test_application_scoped_metrics)
_test_application_index_scoped_metrics.append(
        ('Function/views:index', 1))


@validate_code_level_metrics("views", "index")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('views:index',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index():
    response = test_application.get('/index/')
    assert response.status_code == 200
    response.mustcontain('INDEX RESPONSE')


class TastyPieFullDebugMode(object):
    def __init__(self, tastypie_full_debug):
        from django.conf import settings
        self.settings = settings
        self.tastypie_full_debug = tastypie_full_debug

    def __enter__(self):
        self.settings.TASTYPIE_FULL_DEBUG = self.tastypie_full_debug
        return 500 if self.tastypie_full_debug else 404

    def __exit__(self, *args, **kwargs):
        self.settings.TASTYPIE_FULL_DEBUG = False


_test_api_base_scoped_metrics = [
        ('Function/django.core.handlers.wsgi:WSGIHandler.__call__', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
]

if six.PY3:
    _test_api_base_scoped_metrics.append(
        ('Function/tastypie.resources:Resource.wrap_view.<locals>.wrapper', 1))
else:
    _test_api_base_scoped_metrics.append(
            ('Function/tastypie.resources:wrapper', 1))

# django < 1.12 used the RegexURLResolver class and this was updated to URLResolver in later versions
if VERSION <= (0, 14, 3) and not six.PY3:
    _test_api_base_scoped_metrics.append(('Function/django.urls.resolvers:RegexURLResolver.resolve', 1))
else:
    _test_api_base_scoped_metrics.append(('Function/django.urls.resolvers:URLResolver.resolve', 1))


_test_application_not_found_scoped_metrics = list(
        _test_api_base_scoped_metrics)


@pytest.mark.parametrize('api_version', ['v1', 'v2'])
@pytest.mark.parametrize('tastypie_full_debug', [True, False])
def test_not_found(api_version, tastypie_full_debug):

    _test_application_not_found_scoped_metrics = list(
            _test_api_base_scoped_metrics)

    if tastypie_full_debug:
        _test_application_not_found_scoped_metrics.append(
                ('Function/django.http.response:HttpResponse.close', 1))
    else:
        _test_application_not_found_scoped_metrics.append(
                (('Function/django.http.response:'
                    'HttpResponseNotFound.close'), 1))

    _errors = []

    if tastypie_full_debug:
        _errors.append('tastypie.exceptions:NotFound')

    @validate_transaction_errors(errors=_errors)
    @validate_transaction_metrics('api:SimpleResource.dispatch_detail',
            scoped_metrics=_test_application_not_found_scoped_metrics)
    def _test_not_found():
        with TastyPieFullDebugMode(tastypie_full_debug) as debug_status:
            test_application.get('/api/%s/simple/NotFound/' % api_version,
                    status=debug_status)

    _test_not_found()


_test_application_object_does_not_exist_scoped_metrics = list(
        _test_api_base_scoped_metrics)

_test_application_object_does_not_exist_scoped_metrics.append(
        ('Function/tastypie.http:HttpNotFound.close', 1))


@pytest.mark.parametrize('api_version', ['v1', 'v2'])
@pytest.mark.parametrize('tastypie_full_debug', [True, False])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('api:SimpleResource.dispatch_detail',
        scoped_metrics=_test_application_object_does_not_exist_scoped_metrics)
def test_object_does_not_exist(api_version, tastypie_full_debug):
    with TastyPieFullDebugMode(tastypie_full_debug):
        test_application.get(
                '/api/%s/simple/ObjectDoesNotExist/' % api_version, status=404)


_test_application_raises_zerodivision = list(_test_api_base_scoped_metrics)
_test_application_raises_zerodivision_exceptions = []

if six.PY3:
    _test_application_raises_zerodivision_exceptions.append(
            'builtins:ZeroDivisionError')
else:
    _test_application_raises_zerodivision_exceptions.append(
            'exceptions:ZeroDivisionError')


@pytest.mark.parametrize('api_version', ['v1', 'v2'])
@pytest.mark.parametrize('tastypie_full_debug', [True, False])
@validate_transaction_errors(
        errors=_test_application_raises_zerodivision_exceptions)
def test_raises_zerodivision(api_version, tastypie_full_debug):

    _test_application_raises_zerodivision = list(_test_api_base_scoped_metrics)

    if tastypie_full_debug:
        _test_application_raises_zerodivision.append(
                (('Function/django.core.handlers.exception:'
                    'handle_uncaught_exception'), 1))
    else:
        _test_application_raises_zerodivision.append(
                ('Function/tastypie.http:HttpApplicationError.close', 1))

    @validate_transaction_metrics('api:SimpleResource.dispatch_detail',
            scoped_metrics=_test_application_raises_zerodivision)
    def _test_raises_zerodivision():
        with TastyPieFullDebugMode(tastypie_full_debug):
            test_application.get(
                    '/api/%s/simple/ZeroDivisionError/' % api_version,
                    status=500)

    _test_raises_zerodivision()


@pytest.mark.parametrize('api_version', ['v1', 'v2'])
@pytest.mark.parametrize('tastypie_full_debug', [True, False])
@override_ignore_status_codes(set())  # don't ignore any status codes
@validate_transaction_errors(errors=['tastypie.exceptions:NotFound'])
@validate_transaction_metrics('api:SimpleResource.dispatch_detail',
        scoped_metrics=_test_application_not_found_scoped_metrics)
def test_record_404_errors(api_version, tastypie_full_debug):

    _test_application_not_found_scoped_metrics = list(
            _test_api_base_scoped_metrics)

    if tastypie_full_debug:
        _test_application_not_found_scoped_metrics.append(
                ('Function/django.http.response:HttpResponse.close', 1))
    else:
        _test_application_not_found_scoped_metrics.append(
                (('Function/django.http.response:'
                    'HttpResponseNotFound.close'), 1))

    @validate_transaction_metrics('api:SimpleResource.dispatch_detail',
            scoped_metrics=_test_application_not_found_scoped_metrics)
    def _test_not_found():
        with TastyPieFullDebugMode(tastypie_full_debug) as debug_status:
            test_application.get('/api/%s/simple/NotFound/' % api_version,
                    status=debug_status)

    _test_not_found()


@pytest.mark.parametrize('api_version', ['v1', 'v2'])
@pytest.mark.parametrize('tastypie_full_debug', [True, False])
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('test_application:test_ended_txn_name',
        background_task=True)
@background_task()
def test_ended_txn_name(api_version, tastypie_full_debug):
    # if the transaction has ended, do not change the transaction name
    end_of_transaction()

    with TastyPieFullDebugMode(tastypie_full_debug) as debug_status:
        test_application.get('/api/%s/simple/NotFound/' % api_version,
                status=debug_status)
