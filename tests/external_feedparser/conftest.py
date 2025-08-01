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

from pathlib import Path

import pytest
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture
from testing_support.mock_external_http_server import MockExternalHTTPServer

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (external_feedparser)", default_settings=_default_settings
)


def create_handler(response):
    def handler(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(response)

    return handler


@pytest.fixture(scope="session")
def server():
    with Path("packages.xml").open("rb") as f:
        response = f.read()

    handler = create_handler(response)
    with MockExternalHTTPServer(handler=handler) as server:
        yield server
