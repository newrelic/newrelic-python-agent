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

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_application_settings)

from newrelic.packages import six

from conftest import is_flask_v2 as nested_blueprint_support

skip_if_not_nested_blueprint_support = pytest.mark.skipif(not nested_blueprint_support,
        reason="Requires nested blueprint support. (Flask >=v2.0.0)")


def target_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as we will then get view handler
    # functions are different between Python 2 and 3, with the latter
    # showing <local> scope in path.

    from _test_blueprints import _test_application
    return _test_application

_test_blueprints_index_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_blueprints:index_page', 1),
        ('Function/flask.app:Flask.preprocess_request', 1),
        ('Function/_test_blueprints:before_app_request', 1),
        ('Function/_test_blueprints:before_request', 1),
        ('Function/flask.app:Flask.process_response', 1),
        ('Function/_test_blueprints:after_request', 1),
        ('Function/_test_blueprints:after_app_request', 1),
        ('Function/flask.app:Flask.do_teardown_request', 1),
        ('Function/_test_blueprints:teardown_app_request', 1),
        ('Function/_test_blueprints:teardown_request', 1),
        ('Function/flask.app:Flask.do_teardown_appcontext', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_blueprints:index_page',
        scoped_metrics=_test_blueprints_index_scoped_metrics)
def test_blueprints_index():
    application = target_application()
    response = application.get('/index')
    response.mustcontain('BLUEPRINT INDEX RESPONSE')

_test_blueprints_endpoint_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_blueprints:endpoint_page', 1),
        ('Function/flask.app:Flask.preprocess_request', 1),
        ('Function/_test_blueprints:before_app_request', 1),
        ('Function/flask.app:Flask.process_response', 1),
        ('Function/_test_blueprints:after_app_request', 1),
        ('Function/flask.app:Flask.do_teardown_request', 1),
        ('Function/_test_blueprints:teardown_app_request', 1),
        ('Function/flask.app:Flask.do_teardown_appcontext', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_blueprints:endpoint_page',
        scoped_metrics=_test_blueprints_endpoint_scoped_metrics)
def test_blueprints_endpoint():
    application = target_application()
    response = application.get('/endpoint')
    response.mustcontain('BLUEPRINT ENDPOINT RESPONSE')


_test_blueprints_nested_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_blueprints:nested_page', 1),
        ('Function/flask.app:Flask.preprocess_request', 1),
        ('Function/_test_blueprints:before_app_request', 1),
        ('Function/_test_blueprints:before_request', 1),
        ('Function/flask.app:Flask.process_response', 1),
        ('Function/_test_blueprints:after_request', 1),
        ('Function/_test_blueprints:after_app_request', 1),
        ('Function/flask.app:Flask.do_teardown_request', 1),
        ('Function/_test_blueprints:teardown_app_request', 1),
        ('Function/_test_blueprints:teardown_request', 1),
        ('Function/flask.app:Flask.do_teardown_appcontext', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

@skip_if_not_nested_blueprint_support
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_blueprints:nested_page')
def test_blueprints_nested():
        application = target_application()
        response = application.get('/parent/child/nested')
        response.mustcontain('PARENT NESTED RESPONSE')
