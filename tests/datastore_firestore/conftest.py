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
import uuid

import pytest

from google.cloud.firestore import Client

from testing_support.db_settings import firestore_settings
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture  # noqa: F401; pylint: disable=W0611


DB_SETTINGS = firestore_settings()[0]
FIRESTORE_HOST = DB_SETTINGS["host"]
FIRESTORE_PORT = DB_SETTINGS["port"]

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
    'debug.log_explain_plan_queries': True
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (datastore_firestore)',
        default_settings=_default_settings,
        linked_applications=['Python Agent Test (datastore)'])


@pytest.fixture(scope="session")
def client():
    os.environ["FIRESTORE_EMULATOR_HOST"] = "%s:%d" % (FIRESTORE_HOST, FIRESTORE_PORT)
    client = Client()
    client.collection("healthcheck").document("healthcheck").set({}, retry=None, timeout=5)  # Ensure connection is available
    return client


@pytest.fixture(scope="function")
def collection(client):
    yield client.collection("firestore_collection_" + str(uuid.uuid4()))


@pytest.fixture(scope="function", autouse=True)
def reset_firestore(client):
    for coll in client.collections():
        for document in coll.list_documents():
            document.delete()
