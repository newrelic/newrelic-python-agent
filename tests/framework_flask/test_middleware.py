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

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors

def target_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as we will then get view handler
    # functions are different between Python 2 and 3, with the latter
    # showing <local> scope in path.

    from _test_middleware import _test_application
    return _test_application

_test_application_app_middleware_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_middleware:index_page', 1),
        ('Function/flask.app:Flask.try_trigger_before_first_request_functions', 1),
        ('Function/_test_middleware:before_first_request', 1),
        ('Function/flask.app:Flask.preprocess_request', 1),
        ('Function/_test_middleware:before_request', 1),
        ('Function/flask.app:Flask.process_response', 1),
        ('Function/_test_middleware:after_request', 1),
        ('Function/flask.app:Flask.do_teardown_request', 1),
        ('Function/_test_middleware:teardown_request', 1),
        ('Function/flask.app:Flask.do_teardown_appcontext', 1),
        ('Function/_test_middleware:teardown_appcontext', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_middleware:index_page',
        scoped_metrics=_test_application_app_middleware_scoped_metrics)
@validate_code_level_metrics("_test_middleware", "index_page")
@validate_code_level_metrics("_test_middleware", "before_first_request")
@validate_code_level_metrics("_test_middleware", "before_request")
@validate_code_level_metrics("_test_middleware", "after_request")
@validate_code_level_metrics("_test_middleware", "teardown_request")
@validate_code_level_metrics("_test_middleware", "teardown_appcontext")
def test_application_app_middleware():
    application = target_application()
    response = application.get('/middleware')
    response.mustcontain('INDEX RESPONSE')
