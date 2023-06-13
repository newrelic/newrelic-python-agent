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
    raise_background_exceptions,
    wait_for_background_threads,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.common.package_version_utils import get_package_version

WAITRESS_VERSION = get_package_version("waitress")


@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_wsgi_application_index(target_application):
    @validate_transaction_metrics(
        "_application:sample_application",
        custom_metrics=[
            ("Python/Dispatcher/Waitress/%s" % WAITRESS_VERSION, 1),
        ],
    )
    @raise_background_exceptions()
    @wait_for_background_threads()
    def _test():
        response = target_application.get("/")
        assert response.status == "200 OK"

    _test()


@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_raise_exception_application(target_application):
    @validate_transaction_errors(["builtins:RuntimeError"])
    @validate_transaction_metrics(
        "_application:sample_application",
        custom_metrics=[
            ("Python/Dispatcher/Waitress/%s" % WAITRESS_VERSION, 1),
        ],
    )
    @raise_background_exceptions()
    @wait_for_background_threads()
    def _test():
        response = target_application.get("/raise-exception-application/", status=500)
        assert response.status == "500 Internal Server Error"

    _test()


@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_raise_exception_response(target_application):
    @validate_transaction_errors(["builtins:RuntimeError"])
    @validate_transaction_metrics(
        "_application:sample_application",
        custom_metrics=[
            ("Python/Dispatcher/Waitress/%s" % WAITRESS_VERSION, 1),
        ],
    )
    @raise_background_exceptions()
    @wait_for_background_threads()
    def _test():
        response = target_application.get("/raise-exception-response/", status=500)
        assert response.status == "500 Internal Server Error"

    _test()


@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_raise_exception_finalize(target_application):
    @validate_transaction_errors(["builtins:RuntimeError"])
    @validate_transaction_metrics(
        "_application:sample_application",
        custom_metrics=[
            ("Python/Dispatcher/Waitress/%s" % WAITRESS_VERSION, 1),
        ],
    )
    @raise_background_exceptions()
    @wait_for_background_threads()
    def _test():
        response = target_application.get("/raise-exception-finalize/", status=500)
        assert response.status == "500 Internal Server Error"

    _test()
