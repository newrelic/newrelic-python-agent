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
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_tornado)", default_settings=_default_settings
)


@pytest.fixture(scope="module")
def app(request):
    import tornado
    from _target_application import make_app
    from tornado.testing import AsyncHTTPTestCase

    class App(AsyncHTTPTestCase):
        def get_app(self):
            custom = request.node.get_closest_marker("custom_app")
            return make_app(custom)

        def runTest(self, *args, **kwargs):
            pass

        @property
        def tornado_version(self):
            return ".".join(map(str, tornado.version_info))

    case = App()
    case.setUp()
    yield case
    case.tearDown()
