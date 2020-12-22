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
    validate_transaction_errors)

try:
    # The __version__ attribute was only added in 0.7.0.
    from flask import __version__ as flask_version
    is_gt_flask060 = True
except ImportError:
    is_gt_flask060 = False

requires_error_handler = pytest.mark.skipif(not is_gt_flask060,
        reason="The error handler decorator is not supported.")

def target_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as we will then get view handler
    # functions are different between Python 2 and 3, with the latter
    # showing <local> scope in path.

    from _test_user_exceptions import _test_application
    return _test_application

_test_user_exception_handler_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_user_exceptions:page_not_found', 1),
        ('Function/_test_user_exceptions:error_page', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

if is_gt_flask060:
    _test_user_exception_handler_scoped_metrics.extend([
            ('Function/flask.app:Flask.handle_user_exception', 1)])

@requires_error_handler
@validate_transaction_errors(errors=['_test_user_exceptions:UserException'])
@validate_transaction_metrics('_test_user_exceptions:error_page',
        scoped_metrics=_test_user_exception_handler_scoped_metrics)
def test_user_exception_handler():
    application = target_application()
    response = application.get('/user_exception', status=500)
    response.mustcontain('USER EXCEPTION')
