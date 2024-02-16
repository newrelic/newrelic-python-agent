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

import os
from time import sleep

import pytest
from pinecone import Pinecone, PodSpec
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)

from newrelic.api.transaction import current_transaction

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_explain_plan_queries": True,
    "ml_insights_events.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (datastore_pinecone)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)


@pytest.fixture(scope="function")
def pinecone_instance():
    api_key = os.environ.get("PINECONE_API_KEY")
    pinecone_instance = Pinecone(api_key=api_key)

    # Delete if already exists/did not get properly deleted
    # from previous runs
    if len(pinecone_instance.list_indexes()) > 1:
        pinecone_instance.delete_index("python-test")

    pinecone_instance.create_index(
        name="python-test",
        dimension=4,
        metric="cosine",
        spec=PodSpec(
            environment="us-east-1-aws",
            pod_type="p1.x1",
            pods=1,
        ),
    )

    yield pinecone_instance
    pinecone_instance.delete_index("python-test")


# Note: Do not call this one unless the `pinecone_instance`
# fixture has already been called within the test
@pytest.fixture(scope="function")
def pinecone_index_instance(pinecone_instance):
    index = pinecone_instance.Index("python-test")
    sleep(2)
    yield index
    index.delete("python-test")


@pytest.fixture
def set_trace_info():
    def set_info():
        txn = current_transaction()
        if txn:
            txn.guid = "transaction-id"
            txn._trace_id = "trace-id"

    return set_info
