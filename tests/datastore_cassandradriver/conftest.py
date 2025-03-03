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

import sys

import pytest
from testing_support.db_settings import cassandra_settings
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

DB_SETTINGS = cassandra_settings()
PYTHON_VERSION = sys.version_info
IS_PYPY = hasattr(sys, "pypy_version_info")


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


@pytest.fixture(scope="function", params=["Libev", "AsyncCore", "Twisted"])
def connection_class(request):
    # Configure tests to run against a specific async reactor.
    reactor_name = request.param

    if reactor_name == "Libev":
        if IS_PYPY:
            pytest.skip(reason="Libev not available for PyPy.")
        from cassandra.io.libevreactor import LibevConnection as Connection
    elif reactor_name == "AsyncCore":
        if PYTHON_VERSION >= (3, 12):
            pytest.skip(reason="asyncore was removed from stdlib in Python 3.12.")
        from cassandra.io.asyncorereactor import AsyncoreConnection as Connection
    elif reactor_name == "Twisted":
        from cassandra.io.twistedreactor import TwistedConnection as Connection
    elif reactor_name == "AsyncIO":
        # AsyncIO reactor is experimental and currently non-functional. Not testing it yet.
        from cassandra.io.asyncioreactor import AsyncioConnection as Connection

    return Connection


@pytest.fixture(scope="function")
def cluster_options(connection_class):
    from cassandra.cluster import ExecutionProfile
    from cassandra.policies import RoundRobinPolicy

    load_balancing_policy = RoundRobinPolicy()
    execution_profiles = {
        "default": ExecutionProfile(load_balancing_policy=load_balancing_policy, request_timeout=60.0)
    }
    cluster_options = {
        "contact_points": [(node["host"], node["port"]) for node in DB_SETTINGS],
        "execution_profiles": execution_profiles,
        "connection_class": connection_class,
        "protocol_version": 4,
    }
    yield cluster_options


@pytest.fixture(scope="function")
def cluster(cluster_options):
    from cassandra.cluster import Cluster

    cluster = Cluster(**cluster_options)
    yield cluster
