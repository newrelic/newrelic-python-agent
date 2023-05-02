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

from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors

from newrelic.packages import six


@pytest.fixture(autouse=True, scope="module")
def skip_if_not_cornice():
    pytest.importorskip("cornice")


def target_application():
    # We need to delay Pyramid application creation because of ordering
    # issues whereby the agent needs to be initialised before Pyramid is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as Pyramid relies on view handlers being
    # at global scope, so import it from a separate module.

    from _test_application import target_application as _app
    return _app(False, False, True)

_test_cornice_service_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/_test_application:cornice_service_get_info', 1)]

@validate_code_level_metrics("_test_application", "cornice_service_get_info")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:cornice_service_get_info',
        scoped_metrics=_test_cornice_service_scoped_metrics)
def test_cornice_service():
    application = target_application()
    application.get('/service')

_test_cornice_resource_collection_get_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/_test_application:Resource.collection_get', 1)]

@validate_code_level_metrics("_test_application.Resource", "collection_get")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:Resource.collection_get',
        scoped_metrics=_test_cornice_resource_collection_get_scoped_metrics)
def test_cornice_resource_collection_get():
    application = target_application()
    application.get('/resource')

_test_cornice_resource_get_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/_test_application:Resource.get', 1)]

@validate_code_level_metrics("_test_application.Resource", "get")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:Resource.get',
        scoped_metrics=_test_cornice_resource_get_scoped_metrics)
def test_cornice_resource_get():
    application = target_application()
    application.get('/resource/1')

_test_cornice_error_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/cornice.pyramidhook:handle_exceptions', 1),
        ('Function/_test_application:cornice_error_get_info', 1)]

if six.PY3:
    _test_cornice_error_errors = ['builtins:RuntimeError']
else:
    _test_cornice_error_errors = ['exceptions:RuntimeError']

@validate_code_level_metrics("_test_application", "cornice_error_get_info")
@validate_transaction_errors(errors=_test_cornice_error_errors)
@validate_transaction_metrics('_test_application:cornice_error_get_info',
        scoped_metrics=_test_cornice_error_scoped_metrics)
def test_cornice_error():
    application = target_application()
    with pytest.raises(RuntimeError):
        application.get('/cornice_error', status=500)
