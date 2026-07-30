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
from testing_support.db_settings import redis_settings
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
    app_name="Python Agent Test (datastore_redis)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)

DB_SETTINGS = redis_settings()[0]

REDIS_PY_VERSION = get_package_version_tuple("redis")


@pytest.fixture(scope="session")
def connection_kwargs():
    kwargs = {"host": DB_SETTINGS["host"], "port": DB_SETTINGS["port"], "db": 0}

    if REDIS_PY_VERSION >= (8, 1, 0):
        from redis.maint_notifications import MaintNotificationsConfig

        kwargs["maint_notifications_config"] = MaintNotificationsConfig(enabled=False)

    return kwargs


@pytest.fixture(scope="session", params=("Redis", "StrictRedis"))
def client(request, connection_kwargs):
    def _client():
        import redis

        if request.param == "Redis":
            return redis.Redis(**connection_kwargs)
        else:
            return redis.StrictRedis(**connection_kwargs)

    return _client


@pytest.fixture(scope="session")
def async_client(loop, connection_kwargs):
    def _client():
        import redis

        return loop.run_until_complete(redis.asyncio.Redis(**connection_kwargs))

    return _client


@pytest.fixture
def async_client_pool(loop, connection_kwargs):
    def _client_pool():
        import redis.asyncio

        connection_pool = redis.asyncio.ConnectionPool(**connection_kwargs)
        return loop.run_until_complete(redis.asyncio.Redis(connection_pool=connection_pool))

    return _client_pool
