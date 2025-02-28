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
from testing_support.db_settings import mongodb_settings
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
    app_name="Python Agent Test (datastore_pymongo)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)

DB_SETTINGS = mongodb_settings()[0]
MONGODB_HOST = DB_SETTINGS["host"]
MONGODB_PORT = DB_SETTINGS["port"]
MONGODB_COLLECTION = DB_SETTINGS["collection"]


@pytest.fixture(scope="session", params=["asyncio", "tornado"])
def implementation(request):
    return request.param


@pytest.fixture(scope="session")
def client(implementation):
    from motor.motor_asyncio import AsyncIOMotorClient
    from motor.motor_tornado import MotorClient as TornadoMotorClient

    # Must be actually initialized in test function, so provide a callable that returns the client.
    def _client():
        if implementation == "asyncio":
            return AsyncIOMotorClient(host=MONGODB_HOST, port=MONGODB_PORT)
        else:
            return TornadoMotorClient(host=MONGODB_HOST, port=MONGODB_PORT)

    return _client


@pytest.fixture(scope="session")
def init_metric(implementation):
    if implementation == "asyncio":
        return ("Function/motor.motor_asyncio:AsyncIOMotorClient.__init__", 1)
    else:
        return ("Function/motor.motor_tornado:MotorClient.__init__", 1)
