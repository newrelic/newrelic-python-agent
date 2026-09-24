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
from testing_support.db_settings import opensearch_settings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (datastore_opensearch)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)

OPENSEARCH_SETTINGS = opensearch_settings()[0]
OPENSEARCH_MULTIPLE_SETTINGS = opensearch_settings()
OPENSEARCH_URL = f"http://{OPENSEARCH_SETTINGS['host']}:{OPENSEARCH_SETTINGS['port']}"


@pytest.fixture
def client():
    from opensearchpy import OpenSearch

    _client = OpenSearch(OPENSEARCH_URL)
    yield _client
    _client.close()


@pytest.fixture
def async_client(loop):
    from opensearchpy import AsyncOpenSearch

    # Manual context manager
    _async_client = AsyncOpenSearch(OPENSEARCH_URL)
    yield _async_client
    loop.run_until_complete(_async_client.close())
