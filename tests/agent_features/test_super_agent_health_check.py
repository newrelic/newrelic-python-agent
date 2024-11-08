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
import threading

from newrelic.core.config import finalize_application_settings
from agent_unittests.test_agent_protocol import HttpClientRecorder
from newrelic.core.super_agent_health import is_valid_file_delivery_location, super_agent_health_instance
from newrelic.config import initialize, _reset_configuration_done
from newrelic.core.agent_protocol import AgentProtocol
from newrelic.core.application import Application
from newrelic.network.exceptions import DiscardDataForRequest


@pytest.mark.parametrize("file_uri", ["", "file://", "/test/dir", "foo:/test/dir"])
def test_invalid_file_directory_supplied(file_uri):
    assert is_valid_file_delivery_location(file_uri) is False


def test_write_to_file_healthy_status(monkeypatch, tmp_path):
    # Setup expected env vars to run super agent health check
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_FLEET_ID", "1234")
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_HEALTH_DELIVERY_LOCATION", file_path)

    # Write to health YAML file
    super_agent_instance = super_agent_health_instance()
    super_agent_instance.start_time_unix_nano = "1234567890"
    super_agent_instance.write_to_health_file()

    # Grab the file we just wrote to and read its contents
    health_files = os.listdir(tmp_path)
    path_to_written_file = f"{tmp_path}/{health_files[0]}"
    with open(path_to_written_file, 'r') as f:
        contents = f.readlines()

    # Assert on contents of health file
    assert len(contents) == 4
    assert contents[0] == "healthy: True\n"
    assert contents[1] == "status: Healthy\n"
    assert contents[2] == "start_time_unix_nano: 1234567890\n"
    assert contents[3].startswith("status_time_unix_nano:") is True


def test_write_to_file_unhealthy_status(monkeypatch, tmp_path):
    # Setup expected env vars to run super agent health check
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_FLEET_ID", "1234")
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_HEALTH_DELIVERY_LOCATION", file_path)

    # Write to health YAML file
    super_agent_instance = super_agent_health_instance()
    super_agent_instance.start_time_unix_nano = "1234567890"
    super_agent_instance.set_health_status("invalid_license")
    super_agent_instance.write_to_health_file()

    # Grab the file we just wrote to and read its contents
    health_files = os.listdir(tmp_path)
    path_to_written_file = f"{tmp_path}/{health_files[0]}"
    with open(path_to_written_file, 'r') as f:
        contents = f.readlines()

    # Assert on contents of health file
    assert len(contents) == 5
    assert contents[0] == "healthy: False\n"
    assert contents[1] == "status: Invalid license key (HTTP status code 401)\n"
    assert contents[2] == "start_time_unix_nano: 1234567890\n"
    assert contents[3].startswith("status_time_unix_nano:") is True
    assert contents[4] == "last_error: NR-APM-001\n"


def test_no_override_on_unhealthy_shutdown(monkeypatch, tmp_path):
    # Setup expected env vars to run super agent health check
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_FLEET_ID", "1234")
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_HEALTH_DELIVERY_LOCATION", file_path)

    # Write to health YAML file
    super_agent_instance = super_agent_health_instance()
    super_agent_instance.start_time_unix_nano = "1234567890"
    super_agent_instance.set_health_status("invalid_license")
    # Attempt to override a previously unhealthy status
    super_agent_instance.set_health_status("agent_shutdown")
    super_agent_instance.write_to_health_file()

    # Grab the file we just wrote to and read its contents
    health_files = os.listdir(tmp_path)
    path_to_written_file = f"{tmp_path}/{health_files[0]}"
    with open(path_to_written_file, 'r') as f:
        contents = f.readlines()

    # Assert on contents of health file
    assert len(contents) == 5
    assert contents[0] == "healthy: False\n"
    assert contents[1] == "status: Invalid license key (HTTP status code 401)\n"
    assert contents[4] == "last_error: NR-APM-001\n"


def test_health_check_running_threads(monkeypatch, tmp_path):
    running_threads = threading.enumerate()
    # Only the main thread should be running since not super agent env vars are set
    assert len(running_threads) == 1

    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_FLEET_ID", "1234")
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_HEALTH_DELIVERY_LOCATION", file_path)

    # Re-initialize the agent to allow the health check thread to start and assert that it did
    _reset_configuration_done()
    initialize()
    running_threads = threading.enumerate()

    assert len(running_threads) == 2
    assert running_threads[1].name == "APM-Control-Health-Main-Thread"


def test_proxy_error_status(monkeypatch, tmp_path):
    # Setup expected env vars to run super agent health check
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_FLEET_ID", "1234")
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_HEALTH_DELIVERY_LOCATION", file_path)

    _reset_configuration_done()
    initialize()

    # Mock a 407 error to generate a proxy error health status
    HttpClientRecorder.STATUS_CODE = 407
    settings = finalize_application_settings(
        {
            "license_key": "123LICENSEKEY",
        }
    )
    protocol = AgentProtocol(settings, client_cls=HttpClientRecorder)

    with pytest.raises(DiscardDataForRequest):
        protocol.send("analytic_event_data")

    # Give time for the scheduler to kick in and write to the health file
    time.sleep(5)

    # Grab the file we just wrote to and read its contents
    health_files = os.listdir(tmp_path)
    path_to_written_file = f"{tmp_path}/{health_files[0]}"
    with open(path_to_written_file, 'r') as f:
        contents = f.readlines()

    # Assert on contents of health file
    assert len(contents) == 5
    assert contents[0] == "healthy: False\n"
    assert contents[1] == "status: HTTP Proxy configuration error; response code 407\n"
    assert contents[4] == "last_error: NR-APM-007\n"


def test_multiple_activations_running_threads(monkeypatch, tmp_path):
    # Setup expected env vars to run super agent health check
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_FLEET_ID", "1234")
    file_path = tmp_path.as_uri()
    monkeypatch.setenv("NEW_RELIC_SUPERAGENT_HEALTH_DELIVERY_LOCATION", file_path)

    _reset_configuration_done()
    initialize()
    application_1 = Application("Test App 1")
    application_2 = Application("Test App 2")

    application_1.activate_session()
    application_2.activate_session()

    running_threads = threading.enumerate()

    assert len(running_threads) == 6
    assert running_threads[1].name == "APM-Control-Health-Main-Thread"
    assert running_threads[2].name == "APM-Control-Health-Session-Thread"
    assert running_threads[4].name == "APM-Control-Health-Session-Thread"
