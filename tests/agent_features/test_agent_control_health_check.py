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
import re
import threading
import time

import pytest
from testing_support.fixtures import initialize_agent
from testing_support.http_client_recorder import HttpClientRecorder

from newrelic.config import _reset_configuration_done, initialize
from newrelic.core.agent_control_health import (
    HealthStatus,
    agent_control_health_instance,
    is_valid_file_delivery_location,
)
from newrelic.core.agent_protocol import AgentProtocol
from newrelic.core.application import Application
from newrelic.core.config import finalize_application_settings, global_settings
from newrelic.network.exceptions import DiscardDataForRequest


def get_health_file_contents(tmp_path):
    # Grab the file we just wrote to and read its contents
    health_files = os.listdir(tmp_path)
    path_to_written_file = f"{tmp_path}/{health_files[0]}"
    with open(path_to_written_file, "r") as f:
        contents = f.readlines()
        return contents


@pytest.mark.parametrize("file_uri", ["", "file://", "/test/dir", "foo:/test/dir"])
def test_invalid_file_directory_supplied(file_uri):
    assert not is_valid_file_delivery_location(file_uri)


def test_agent_control_not_enabled(monkeypatch, tmp_path):
    # Only monkeypatch a valid file URI for delivery location to test default "NEW_RELIC_AGENT_CONTROL_ENABLED" behavior
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", file_path)

    assert not agent_control_health_instance().health_check_enabled


def test_write_to_file_healthy_status(monkeypatch, tmp_path):
    # Setup expected env vars to run agent control health check
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_ENABLED", True)
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", file_path)

    # Write to health YAML file
    agent_control_instance = agent_control_health_instance()
    agent_control_instance.start_time_unix_nano = "1234567890"
    agent_control_instance.write_to_health_file()

    contents = get_health_file_contents(tmp_path)

    # Assert on contents of health file
    assert len(contents) == 4
    assert contents[0] == "healthy: True\n"
    assert contents[1] == "status: Healthy\n"
    assert int(re.search(r"status_time_unix_nano: (\d+)", contents[3]).group(1)) > 0


def test_write_to_file_unhealthy_status(monkeypatch, tmp_path):
    # Setup expected env vars to run agent control health check
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_ENABLED", True)
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", file_path)

    # Write to health YAML file
    agent_control_instance = agent_control_health_instance()
    agent_control_instance.start_time_unix_nano = "1234567890"
    agent_control_instance.set_health_status(HealthStatus.INVALID_LICENSE.value)

    agent_control_instance.write_to_health_file()

    contents = get_health_file_contents(tmp_path)

    # Assert on contents of health file
    assert len(contents) == 5
    assert contents[0] == "healthy: False\n"
    assert contents[1] == "status: Invalid license key (HTTP status code 401)\n"
    assert contents[2] == "start_time_unix_nano: 1234567890\n"
    assert int(re.search(r"status_time_unix_nano: (\d+)", contents[3]).group(1)) > 0
    assert contents[4] == "last_error: NR-APM-001\n"


def test_no_override_on_unhealthy_shutdown(monkeypatch, tmp_path):
    # Setup expected env vars to run agent control health check
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_ENABLED", True)
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", file_path)

    # Write to health YAML file
    agent_control_instance = agent_control_health_instance()
    agent_control_instance.start_time_unix_nano = "1234567890"
    agent_control_instance.set_health_status(HealthStatus.INVALID_LICENSE.value)

    # Attempt to override a previously unhealthy status
    agent_control_instance.set_health_status(HealthStatus.AGENT_SHUTDOWN.value)
    agent_control_instance.write_to_health_file()

    contents = get_health_file_contents(tmp_path)

    # Assert on contents of health file
    assert len(contents) == 5
    assert contents[0] == "healthy: False\n"
    assert contents[1] == "status: Invalid license key (HTTP status code 401)\n"
    assert contents[4] == "last_error: NR-APM-001\n"


def test_health_check_running_threads(monkeypatch, tmp_path):
    running_threads = threading.enumerate()
    # Only the main thread should be running since not agent control env vars are set
    assert len(running_threads) == 1

    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_ENABLED", True)
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", file_path)

    # Re-initialize the agent to allow the health check thread to start and assert that it did
    _reset_configuration_done()
    initialize()

    running_threads = threading.enumerate()

    # Two expected threads: One main agent thread and one main health thread since we have no additional active sessions
    assert len(running_threads) == 2
    assert running_threads[1].name == "Agent-Control-Health-Main-Thread"


def test_proxy_error_status(monkeypatch, tmp_path):
    # Setup expected env vars to run agent control health check
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_ENABLED", True)
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", file_path)

    _reset_configuration_done()
    initialize()

    # Mock a 407 error to generate a proxy error health status
    HttpClientRecorder.STATUS_CODE = 407
    settings = finalize_application_settings({"license_key": "123LICENSEKEY"})
    protocol = AgentProtocol(settings, client_cls=HttpClientRecorder)

    with pytest.raises(DiscardDataForRequest):
        protocol.send("analytic_event_data")

    # Give time for the scheduler to kick in and write to the health file
    time.sleep(5)

    contents = get_health_file_contents(tmp_path)

    # Assert on contents of health file
    assert len(contents) == 5
    assert contents[0] == "healthy: False\n"
    assert contents[1] == "status: HTTP Proxy configuration error; response code 407\n"
    assert contents[4] == "last_error: NR-APM-007\n"


def test_multiple_activations_running_threads(monkeypatch, tmp_path):
    # Setup expected env vars to run agent control health check
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_ENABLED", True)
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", file_path)

    _reset_configuration_done()
    initialize()

    application_1 = Application("Test App 1")
    application_2 = Application("Test App 2")

    application_1.activate_session()
    application_2.activate_session()

    running_threads = threading.enumerate()

    # 6 threads expected: One main agent thread, two active session threads, one main health check thread, and two
    # active session health threads
    assert len(running_threads) == 6
    assert running_threads[1].name == "Agent-Control-Health-Main-Thread"
    assert running_threads[2].name == "Agent-Control-Health-Session-Thread"
    assert running_threads[4].name == "Agent-Control-Health-Session-Thread"


def test_update_to_healthy(monkeypatch, tmp_path):
    # Setup expected env vars to run agent control health check
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_ENABLED", True)
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", file_path)

    _reset_configuration_done()

    # Write to health YAML file
    agent_control_instance = agent_control_health_instance()
    agent_control_instance.start_time_unix_nano = "1234567890"
    agent_control_instance.set_health_status(HealthStatus.FORCED_DISCONNECT.value)

    # Send a successful data batch to enable health status to update to "healthy"
    HttpClientRecorder.STATUS_CODE = 200
    settings = finalize_application_settings({"license_key": "123LICENSEKEY"})
    protocol = AgentProtocol(settings, client_cls=HttpClientRecorder)
    protocol.send("analytic_event_data")

    agent_control_instance.write_to_health_file()

    contents = get_health_file_contents(tmp_path)

    # Assert on contents of health file
    assert contents[0] == "healthy: True\n"
    assert contents[1] == "status: Healthy\n"


def test_max_app_name_status(monkeypatch, tmp_path):
    # Setup expected env vars to run agent control health check
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_ENABLED", True)
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", file_path)

    _reset_configuration_done()
    initialize_agent(app_name="test1;test2;test3;test4")
    # Give time for the scheduler to kick in and write to the health file
    time.sleep(5)

    contents = get_health_file_contents(tmp_path)

    # Assert on contents of health file
    assert len(contents) == 5
    assert contents[0] == "healthy: False\n"
    assert contents[1] == "status: The maximum number of configured app names (3) exceeded\n"
    assert contents[4] == "last_error: NR-APM-006\n"

    # Set app name back to original name specific
    settings = global_settings()
    settings.app_name = "Python Agent Test (agent_features)"
