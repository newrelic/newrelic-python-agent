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
from testing_support.db_settings import elasticsearch_settings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

from newrelic.common.package_version_utils import get_package_version_tuple

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (datastore_elasticsearch)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)

ES_SETTINGS = elasticsearch_settings()[0]
ES_MULTIPLE_SETTINGS = elasticsearch_settings()
ES_URL = f"http://{ES_SETTINGS['host']}:{ES_SETTINGS['port']}"
ES_VERSION = get_package_version_tuple("elasticsearch")

IS_V8_OR_ABOVE = ES_VERSION >= (8,)
IS_V7_OR_BELOW = not IS_V8_OR_ABOVE
RUN_IF_V8_OR_ABOVE = pytest.mark.skipif(not IS_V8_OR_ABOVE, reason="Unsupported for elasticsearch>=8")
RUN_IF_V7_OR_BELOW = pytest.mark.skipif(not IS_V7_OR_BELOW, reason="Unsupported for elasticsearch<=7")


@pytest.fixture
def client():
    from elasticsearch import Elasticsearch

    _client = Elasticsearch(ES_URL)
    yield _client
    _client.close()


@pytest.fixture
def async_client(loop):
    from elasticsearch import AsyncElasticsearch

    # Manual context manager
    _async_client = AsyncElasticsearch(ES_URL)
    yield _async_client
    loop.run_until_complete(_async_client.close())
