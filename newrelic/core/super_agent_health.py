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

import logging
import os
import uuid
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
import sched

_logger = logging.getLogger(__name__)


HEALTH_CHECK_STATUSES = {
    "healthy": ("NR-APM-000", "Healthy"),
    "invalid_license": ("NR-APM-001", "Invalid license key (HTTP status code 401)"),
    "missing_license": ("NR-APM-002", "License key missing in configuration"),
    "forced_disconnect": ("NR-APM-003", "Forced disconnect received from New Relic (HTTP status code 410)"),
    "http_error": ("NR-APM-004", "HTTP error response code received from New Relic"),
    # "max_app_names": ("NR-APM-006", "The maximum number of configured app names (3) exceeded"),
    "proxy_error": ("NR-APM-007", "HTTP Proxy configuration error"),
    "agent_disabled": ("NR-APM-008", "Agent is disabled via configuration"),
    "agent_shutdown": ("NR-APM-099", "Agent has shutdown"),
}


def is_valid_file_delivery_location(file_uri):
    if not file_uri:
        _logger.warning(
            "Configured APM Control health delivery location is empty. APM Control health check will not be enabled."
        )
        return False

    try:
        parsed_uri = urlparse(file_uri)

        if not parsed_uri.scheme or not parsed_uri.path:
            _logger.warning(
                "Configured Super Agent health delivery location is not a complete file URI. Super Agent health check "
                "will not be enabled. "
            )
            return False

        if parsed_uri.scheme != "file":
            _logger.warning(
                "Configured Super Agent health delivery location does not have a valid scheme. Super Agent health "
                "check will not be enabled. "
            )
            return False

        path = Path(parsed_uri.path)

        # Check if the path exists
        if not path.exists():
            _logger.warning(
                "Configured Super Agent health delivery location does not exist. Super Agent health check will not be "
                "enabled. "
            )
            return False

        return True

    except Exception as e:
        _logger.warning(
            "Configured Super Agent health delivery location is not valid. Super Agent health check will not be "
            "enabled. "
        )
        return False


def health_check_enabled():
    fleet_id_present = os.environ.get("NEW_RELIC_SUPERAGENT_FLEET_ID", None)
    if not fleet_id_present:
        _logger.warning("Super Agent fleet ID not found in environment. Health reporting will not be enabled.")
        return False

    health_file_location = os.environ.get("NEW_RELIC_SUPERAGENT_HEALTH_DELIVERY_LOCATION", None)
    valid_file_location = is_valid_file_delivery_location(health_file_location)
    if not valid_file_location:
        return False

    return True


class SuperAgentHealth:
    _instance_lock = threading.Lock()
    _instance = None

    # Define a way to access/create a single super agent object instance similar to the agent_singleton
    @staticmethod
    def super_agent_health_singleton():
        if SuperAgentHealth._instance:
            return SuperAgentHealth._instance

        with SuperAgentHealth._instance_lock:
            if not SuperAgentHealth._instance:
                instance = SuperAgentHealth()

                SuperAgentHealth._instance = instance

        return SuperAgentHealth._instance

    def __init__(self):
        self.last_error = "NR-APM-000"
        self.status = "Healthy"
        self.start_time_unix_nano = None
        self.pid_file_id_map = {}

    def set_health_status(self, health_status, response_code=None, info=None):
        last_error, current_status = HEALTH_CHECK_STATUSES[health_status]

        # Update status messages to be more descriptive if necessary data is present
        if health_status == "http_error" and response_code and info:
            current_status = (
                f"HTTP error response code {response_code} received from New Relic while sending data type {info}"
            )

        if health_status == "proxy_error" and response_code:
            current_status = f"HTTP Proxy configuration error; response code {response_code}"

        # Do not override status with agent_shutdown unless the agent was previously healthy
        if health_status == "agent_shutdown" and self.status != "Healthy":
            pass

        else:
            self.last_error = last_error
            self.status = current_status

    def check_for_healthy_status(self):
        # If our unhealthy status code was not config related, it is possible it could be resolved during an active
        # session. We determine the status is resolved by calling this function when a 200 status code is received to
        # check if the current status is resolvable

        # Checking for forced disconnects or proxy/ HTTP errors
        non_config_error_codes = frozenset(["NR-APM-003", "NR-APM-004", "NR-APM-007"])
        if self.last_error in non_config_error_codes:
            self.last_error = "NR-APM-000"
            self.status = "Healthy"

    def write_to_health_file(self):
        is_healthy = True if self.status == "Healthy" else False
        status_time_unix_nano = time.time_ns()
        health_file_location = os.environ.get("NEW_RELIC_SUPERAGENT_HEALTH_DELIVERY_LOCATION", None)

        health_file_location = str(health_file_location)
        file_path = urlparse(health_file_location).path
        pid = os.getpid()
        file_ids = self.get_file_id(pid)

        file_name = f"health-{file_ids}.yml"
        full_path = os.path.join(file_path, file_name)

        try:
            with open(full_path, "w") as f:
                f.write(f"healthy: {is_healthy}\n")
                f.write(f"status: {self.status}\n")
                f.write(f"start_time_unix_nano: {self.start_time_unix_nano}\n")
                f.write(f"status_time_unix_nano: {status_time_unix_nano}\n")
                if not is_healthy:
                    f.write(f"last_error: {self.last_error}\n")
        except:
            _logger.warning("Unable to write to agent health file.")

    def get_file_id(self, pid):
        # Each file name should have a UUID with hyphens stripped appended to it
        file_id = str(uuid.uuid4()).replace("-", "")

        # Map the UUID to the process ID to ensure each agent instance has one UUID associated with it
        if pid in self.pid_file_id_map:
            pass
        else:
            self.pid_file_id_map[pid] = file_id

        return self.pid_file_id_map[pid]


def super_agent_health_instance():
    # Helper function directly returns the singleton instance similar to agent_instance()
    return SuperAgentHealth.super_agent_health_singleton()


def super_agent_healthcheck_loop():
    reporting_frequency = os.environ.get("NEW_RELIC_SUPERAGENT_HEALTH_FREQUENCY", 5)
    scheduler = sched.scheduler(time.time, time.sleep)

    # Target this function when starting super agent health check threads to keep the scheduler running
    scheduler.enter(reporting_frequency, 1, super_agent_healthcheck, (scheduler, reporting_frequency))
    scheduler.run()


def super_agent_healthcheck(scheduler, reporting_frequency):
    scheduler.enter(reporting_frequency, 1, super_agent_healthcheck, (scheduler, reporting_frequency))

    super_agent_health_instance().write_to_health_file()
