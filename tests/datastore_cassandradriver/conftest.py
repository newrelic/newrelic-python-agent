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
from testing_support.db_settings import cassandra_settings
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)

DB_SETTINGS = cassandra_settings()
HOST = DB_SETTINGS[0]["host"]
PORT = DB_SETTINGS[0]["port"]


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
    app_name="Python Agent Test (datastore_cassandradriver)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)


@pytest.fixture(scope="function")
def cluster():
    from cassandra.cluster import Cluster, ExecutionProfile
    from cassandra.policies import RoundRobinPolicy

    # from cassandra.io.asyncioreactor import AsyncioConnection
    load_balancing_policy = RoundRobinPolicy()
    execution_profiles = {
        "default": ExecutionProfile(load_balancing_policy=load_balancing_policy, request_timeout=60.0)
    }
    cluster = Cluster(
        [(HOST, PORT)],
        execution_profiles=execution_profiles,
        protocol_version=4,
    )

    yield cluster
