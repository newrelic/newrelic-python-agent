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
from google.cloud.firestore import AsyncClient, Client
from testing_support.db_settings import firestore_settings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.time_trace import current_trace
from newrelic.common.system_info import LOCALHOST_EQUIVALENTS, gethostname

DB_SETTINGS = firestore_settings()[0]
FIRESTORE_HOST = DB_SETTINGS["host"]
FIRESTORE_PORT = DB_SETTINGS["port"]

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_explain_plan_queries": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (datastore_firestore)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)


@pytest.fixture()
def instance_info():
    host = gethostname() if FIRESTORE_HOST in LOCALHOST_EQUIVALENTS else FIRESTORE_HOST
    return {
        "host": host,
        "port_path_or_id": str(FIRESTORE_PORT),
        "db.instance": "projects/google-cloud-firestore-emulator/databases/(default)",
    }


@pytest.fixture(scope="session")
def client():
    os.environ["FIRESTORE_EMULATOR_HOST"] = f"{FIRESTORE_HOST}:{FIRESTORE_PORT}"
    client = Client()
    # Ensure connection is available
    client.collection("healthcheck").document("healthcheck").set({}, retry=None, timeout=5)
    return client


@pytest.fixture(scope="function")
def collection(client):
    collection_ = client.collection(f"firestore_collection_{str(uuid.uuid4())}")
    yield collection_
    client.recursive_delete(collection_)


@pytest.fixture(scope="session")
def async_client(loop):
    os.environ["FIRESTORE_EMULATOR_HOST"] = f"{FIRESTORE_HOST}:{FIRESTORE_PORT}"
    client = AsyncClient()
    loop.run_until_complete(
        client.collection("healthcheck").document("healthcheck").set({}, retry=None, timeout=5)
    )  # Ensure connection is available
    return client


@pytest.fixture(scope="function")
def async_collection(async_client, collection):
    # Use the same collection name as the collection fixture
    yield async_client.collection(collection.id)


@pytest.fixture(scope="session")
def assert_trace_for_generator():
    def _assert_trace_for_generator(generator_func, *args, **kwargs):
        txn = current_trace()
        assert not isinstance(txn, DatastoreTrace)

        # Check for generator trace on collections
        _trace_check = []
        for _ in generator_func(*args, **kwargs):
            # Iterate over generator and check trace is correct for each item.
            # Ignore linter, don't use list comprehensions or it's harder to understand the behavior.
            _trace_check.append(isinstance(current_trace(), DatastoreTrace))  # noqa: PERF401
        assert _trace_check and all(_trace_check)  # All checks are True, and at least 1 is present.
        assert current_trace() is txn  # Generator trace has exited.

    return _assert_trace_for_generator


@pytest.fixture(scope="session")
def assert_trace_for_async_generator(loop):
    def _assert_trace_for_async_generator(generator_func, *args, **kwargs):
        _trace_check = []
        txn = current_trace()
        assert not isinstance(txn, DatastoreTrace)

        async def coro():
            # Check for generator trace on collections
            async for _ in generator_func(*args, **kwargs):
                # Iterate over async generator and check trace is correct for each item.
                # Ignore linter, don't use list comprehensions or it's harder to understand the behavior.
                _trace_check.append(isinstance(current_trace(), DatastoreTrace))  # noqa: PERF401

        loop.run_until_complete(coro())

        assert _trace_check and all(_trace_check)  # All checks are True, and at least 1 is present.
        assert current_trace() is txn  # Generator trace has exited.

    return _assert_trace_for_async_generator
