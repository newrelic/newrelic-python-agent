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
from testing_support.fixture.event_loop import (  # noqa: F401; pylint: disable=W0611
    event_loop as loop,
)
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)
from testing_support.db_settings import nginx_settings

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (external_httpx)", default_settings=_default_settings
)


@pytest.fixture(scope="session")
def httpx():
    import httpx

    return httpx


@pytest.fixture(scope="session")
def real_server():
    settings = nginx_settings()[0]

    class RealHTTP2Server:
        host = settings["host"]
        port = settings["http2_port"]

    yield RealHTTP2Server


@pytest.fixture(scope="function")
def sync_client(httpx):
    return httpx.Client()


@pytest.fixture(scope="function")
def async_client(httpx):
    return httpx.AsyncClient()
