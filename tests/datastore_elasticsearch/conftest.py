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

from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture  # noqa: F401; pylint: disable=W0611

from newrelic.common.package_version_utils import get_package_version


_default_settings = {
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

ES_VERSION = tuple([int(n) for n in get_package_version("elasticsearch").split(".")])
ES_SETTINGS = elasticsearch_settings()[0]
ES_MULTIPLE_SETTINGS = elasticsearch_settings()
ES_URL = "http://%s:%s" % (ES_SETTINGS["host"], ES_SETTINGS["port"])


@pytest.fixture(scope="session")
def client():
    from elasticsearch import Elasticsearch

    return Elasticsearch(ES_URL)
