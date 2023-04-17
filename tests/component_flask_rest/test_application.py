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
from testing_support.fixtures import (
    override_generic_settings,
    override_ignore_status_codes,
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

from newrelic.common.object_names import callable_name
from newrelic.core.config import global_settings
from newrelic.packages import six

TEST_APPLICATION_PREFIX = "_test_application.create_app.<locals>" if six.PY3 else "_test_application"


@pytest.fixture(params=["flask_restful", "flask_restx"])
def application(request):
    from _test_application import get_test_application

    if request.param == "flask_restful":
        import flask_restful as module
    elif request.param == "flask_restx":
        import flask_restx as module
    else:
        assert False

    if "propagate_exceptions" in request.fixturenames:
        propagate_exceptions = request.getfixturevalue("propagate_exceptions")
    else:
        propagate_exceptions = False
    return get_test_application(module, propagate_exceptions)


_test_application_index_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_test_application:index", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
]


@validate_code_level_metrics(TEST_APPLICATION_PREFIX + ".IndexResource", "get")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics("_test_application:index", scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index(application):
    response = application.get("/index")
    response.mustcontain("hello")


_test_application_raises_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Function/_test_application:exception", 1),
]


@pytest.mark.parametrize(
    "exception,status_code,ignore_status_code,propagate_exceptions",
    [
        ("werkzeug.exceptions:HTTPException", 404, False, False),
        ("werkzeug.exceptions:HTTPException", 404, True, False),
        ("werkzeug.exceptions:HTTPException", 503, False, False),
        ("_test_application:CustomException", 500, False, False),
        ("_test_application:CustomException", 500, False, True),
    ],
)
def test_application_raises(exception, status_code, ignore_status_code, propagate_exceptions, application):
    @validate_code_level_metrics(TEST_APPLICATION_PREFIX + ".ExceptionResource", "get")
    @validate_transaction_metrics("_test_application:exception", scoped_metrics=_test_application_raises_scoped_metrics)
    def _test():
        try:
            application.get("/exception/%s/%i" % (exception, status_code), status=status_code, expect_errors=True)
        except Exception as e:
            assert propagate_exceptions

            # check that the exception is the expected one
            if callable_name(type(e)) != exception:
                raise

    if ignore_status_code:
        _test = validate_transaction_errors(errors=[])(_test)
        _test = override_ignore_status_codes([status_code])(_test)
    else:
        _test = validate_transaction_errors(errors=[exception])(_test)
        _test = override_ignore_status_codes([])(_test)

    _test()


def test_application_outside_transaction(application):

    _settings = global_settings()

    @override_generic_settings(_settings, {"enabled": False})
    def _test():
        application.get("/exception/werkzeug.exceptions:HTTPException/404", status=404)

    _test()
