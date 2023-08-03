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
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)

from newrelic.api.background_task import background_task


@pytest.fixture(scope="session", params=["sync-sync", "async-sync", "async-async", "asgi-sync", "asgi-async"])
def target_application(request):
    from ._target_application import target_application

    target_application = target_application[request.param]

    try:
        import strawberry

        version = strawberry.__version__
    except Exception:
        import pkg_resources

        version = pkg_resources.get_distribution("strawberry-graphql").version

    is_asgi = "asgi" in request.param
    schema_type = request.param.split("-")[1]

    assert version is not None
    return "Strawberry", version, target_application, not is_asgi, schema_type, 0


@pytest.mark.parametrize("capture_introspection_setting", (True, False))
def test_introspection_transactions(target_application, capture_introspection_setting):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application

    txn_ct = 1 if capture_introspection_setting else 0

    @override_application_settings(
        {"instrumentation.graphql.capture_introspection_queries": capture_introspection_setting}
    )
    @validate_transaction_count(txn_ct)
    @background_task()
    def _test():
        response = target_application("{ __schema { types { name } } }")

    _test()
