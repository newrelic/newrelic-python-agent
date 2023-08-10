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

from conftest import (  # pylint: disable=E0611
    async_handler_support,
    skip_if_not_async_handler_support,
)
from testing_support.validators.validate_code_level_metrics import (
    validate_code_level_metrics,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/flask.app:Flask.preprocess_request", 1),
    ("Function/flask.app:Flask.process_response", 1),
    ("Function/flask.app:Flask.do_teardown_request", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
]


def target_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as we will then get view handler
    # functions are different between Python 2 and 3, with the latter
    # showing <local> scope in path.

    if not async_handler_support:
        from _test_views import _test_application
    else:
        from _test_views_async import _test_application
    return _test_application


@validate_code_level_metrics("_test_views.TestView", "dispatch_request")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics("_test_views:test_view", scoped_metrics=scoped_metrics)
def test_class_based_view():
    application = target_application()
    response = application.get("/view")
    response.mustcontain("VIEW RESPONSE")


@skip_if_not_async_handler_support
@validate_code_level_metrics("_test_views_async.TestAsyncView", "dispatch_request")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics("_test_views_async:test_async_view", scoped_metrics=scoped_metrics)
def test_class_based_async_view():
    application = target_application()
    response = application.get("/async_view")
    response.mustcontain("ASYNC VIEW RESPONSE")


@validate_code_level_metrics("_test_views.TestMethodView", "get")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics("_test_views:test_methodview", scoped_metrics=scoped_metrics)
def test_get_method_view():
    application = target_application()
    response = application.get("/methodview")
    response.mustcontain("METHODVIEW GET RESPONSE")


@validate_code_level_metrics("_test_views.TestMethodView", "post")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics("_test_views:test_methodview", scoped_metrics=scoped_metrics)
def test_post_method_view():
    application = target_application()
    response = application.post("/methodview")
    response.mustcontain("METHODVIEW POST RESPONSE")


@skip_if_not_async_handler_support
@validate_code_level_metrics("_test_views_async.TestAsyncMethodView", "get")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics("_test_views_async:test_async_methodview", scoped_metrics=scoped_metrics)
def test_get_method_async_view():
    application = target_application()
    response = application.get("/async_methodview")
    response.mustcontain("ASYNC METHODVIEW GET RESPONSE")
