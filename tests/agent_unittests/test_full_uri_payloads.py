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
import time

import pytest
from testing_support.fixtures import collector_agent_registration_fixture

from newrelic.common.agent_http import HttpClient
from newrelic.core.agent_protocol import AgentProtocol
from newrelic.core.config import _environ_as_bool, global_settings

DEVELOPER_MODE = _environ_as_bool("NEW_RELIC_DEVELOPER_MODE", False) or "NEW_RELIC_LICENSE_KEY" not in os.environ
SKIP_IF_DEVELOPER_MODE = pytest.mark.skipif(DEVELOPER_MODE, reason="Cannot connect to collector in developer mode")


class FullUriClient(HttpClient):
    def send_request(self, method="POST", path="/agent_listener/invoke_raw_method", *args, **kwargs):
        path = f"https://{self._host}{path}"
        return super(FullUriClient, self).send_request(method, path, *args, **kwargs)


_default_settings = {
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "startup_timeout": 10.0,
}
application = collector_agent_registration_fixture(
    app_name="Python Agent Test (test_full_uri_payloads)", default_settings=_default_settings
)


@pytest.fixture
def session(application):
    session = application._agent.application(application.name)._active_session
    return session


NOW = time.time()
EMPTY_SAMPLES = {"reservoir_size": 100, "events_seen": 0}


@SKIP_IF_DEVELOPER_MODE
@pytest.mark.parametrize(
    "method,payload",
    [
        ("metric_data", []),
        ("analytic_event_data", []),
        ("custom_event_data", []),
        ("error_event_data", []),
        ("transaction_sample_data", []),
        ("sql_trace_data", []),
        ("get_agent_commands", []),
        ("profile_data", []),
        ("error_data", []),
        ("span_event_data", []),
        ("agent_command_results", ["", {"0": {}}]),
    ],
)
def test_full_uri_payload(session, method, payload):
    redirect_host = session._protocol.client._host
    if method == "agent_command_results":
        payload[0] = session.configuration.agent_run_id
    protocol = AgentProtocol(session.configuration, redirect_host, client_cls=FullUriClient)
    # An exception will be raised here if there's a problem with the response
    protocol.send(method, payload)


@SKIP_IF_DEVELOPER_MODE
def test_full_uri_connect():
    # An exception will be raised here if there's a problem with the response
    AgentProtocol.connect(
        "Python Agent Test (test_full_uri_payloads)", [], [], global_settings(), client_cls=FullUriClient
    )
