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
import sched
import threading
import time
import uuid
from enum import IntEnum
from pathlib import Path
from urllib.parse import urlparse


_logger = logging.getLogger(__name__)


class HealthStatus(IntEnum):
    HEALTHY = 0
    INVALID_LICENSE = 1
    MISSING_LICENSE = 2
    FORCED_DISCONNECT = 3
    HTTP_ERROR = 4
    PROXY_ERROR = 7
    AGENT_DISABLED = 8
    FAILED_NR_CONNECTION = 9
    INVALID_CONFIG = 10
    AGENT_SHUTDOWN = 99


# Set enum integer values as dict keys to reduce performance impact of string copies
HEALTH_CHECK_STATUSES = {
    HealthStatus.HEALTHY.value: "Healthy",
    HealthStatus.INVALID_LICENSE.value: "Invalid license key (HTTP status code 401)",
    HealthStatus.MISSING_LICENSE.value: "License key missing in configuration",
    HealthStatus.FORCED_DISCONNECT.value: "Forced disconnect received from New Relic (HTTP status code 410)",
    HealthStatus.HTTP_ERROR.value: "HTTP error response code {response_code} received from New Relic while sending data type {info}",
    HealthStatus.PROXY_ERROR.value: "HTTP Proxy configuration error; response code {response_code}",
    HealthStatus.AGENT_DISABLED.value: "Agent is disabled via configuration",
    HealthStatus.FAILED_NR_CONNECTION.value: "Failed to connect to New Relic data collector",
    HealthStatus.INVALID_CONFIG.value: "Agent config file is not able to be parsed",
    HealthStatus.AGENT_SHUTDOWN.value: "Agent has shutdown",
}
UNKNOWN_STATUS_MESSAGE = "Unknown health status code."
HEALTHY_STATUS_MESSAGE = HEALTH_CHECK_STATUSES[HealthStatus.HEALTHY.value]  # Assign most used status a symbol

PROTOCOL_ERROR_CODES = frozenset(
    [HealthStatus.FORCED_DISCONNECT.value, HealthStatus.HTTP_ERROR.value, HealthStatus.PROXY_ERROR.value]
)
LICENSE_KEY_ERROR_CODES = frozenset([HealthStatus.INVALID_LICENSE.value, HealthStatus.MISSING_LICENSE.value])


def is_valid_file_delivery_location(file_uri):
    # Verify whether file directory provided to agent via env var is a valid file URI to determine whether health
    # check should run
    try:
        parsed_uri = urlparse(file_uri)
        breakpoint()
        if not parsed_uri.scheme or not parsed_uri.path:
            _logger.warning(
                "Configured Agent Control health delivery location is not a complete file URI. Health check will not be "
                "enabled. "
            )
            return False

        if parsed_uri.scheme != "file":
            _logger.warning(
                "Configured Agent Control health delivery location does not have a valid scheme. Health check will not be "
                "enabled."
            )
            return False

        path = Path(parsed_uri.path)

        # Check if the path exists
        if not path.exists():
            _logger.warning(
                "Configured Agent Control health delivery location does not exist. Health check will not be enabled."
            )
            return False

        return True

    except Exception as e:
        _logger.warning(
            "Configured Agent Control health delivery location is not valid. Health check will not be enabled."
        )
        return False


class AgentControlHealth:
    _instance_lock = threading.Lock()
    _instance = None

    # Define a way to access/create a single agent control object instance similar to the agent_singleton
    @staticmethod
    def agent_control_health_singleton():
        if AgentControlHealth._instance:
            return AgentControlHealth._instance

        with AgentControlHealth._instance_lock:
            if not AgentControlHealth._instance:
                instance = AgentControlHealth()

                AgentControlHealth._instance = instance

        return AgentControlHealth._instance

    def __init__(self):
        # Initialize health check with a healthy status that can be updated as issues are encountered
        self.status_code = HealthStatus.HEALTHY.value
        self.status_message = HEALTHY_STATUS_MESSAGE
        self.start_time_unix_nano = None
        self.pid_file_id_map = {}

    @property
    def health_check_enabled(self):
        # Default to False - this must be explicitly set to True by the sidecar/ operator to enable health check
        agent_control_enabled = os.environ.get("NEW_RELIC_AGENT_CONTROL_ENABLED", False)
        if not agent_control_enabled:
            return False

        health_file_location = os.environ.get(
            "NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", "file:///newrelic/apm/health"
        )
        # Explicitly check if the variable was set to an empty string so we can assign the default
        if not health_file_location:
            health_file_location = "file:///newrelic/apm/health"

        return is_valid_file_delivery_location(health_file_location)

    @property
    def is_healthy(self):
        return self.status_code == HealthStatus.HEALTHY.value

    def set_health_status(self, status_code, response_code=None, info=None):
        previous_status_code = self.status_code

        if status_code == HealthStatus.FAILED_NR_CONNECTION.value and previous_status_code in LICENSE_KEY_ERROR_CODES:
            # Do not update to failed connection status when license key is the issue
            return
        elif status_code == HealthStatus.AGENT_SHUTDOWN.value and not self.is_healthy:
            # Do not override status with agent_shutdown unless the agent was previously healthy
            return

        status_message = HEALTH_CHECK_STATUSES.get(status_code, UNKNOWN_STATUS_MESSAGE)
        self.status_message = status_message.format(response_code=response_code, info=info)
        self.status_code = status_code

    def update_to_healthy_status(self, protocol_error=False, collector_error=False):
        # If our unhealthy status code was not config related, it is possible it could be resolved during an active
        # session. This function allows us to update to a healthy status if so based on the error type
        # Since this function is only called when we are in scenario where the agent functioned as expected, we check to
        # see if the previous status was unhealthy so we know to update it
        if (
            protocol_error
            and self.status_code in PROTOCOL_ERROR_CODES
            or collector_error
            and self.status_code == HealthStatus.FAILED_NR_CONNECTION.value
        ):
            self.status_code = HealthStatus.HEALTHY.value
            self.status_message = HEALTHY_STATUS_MESSAGE

    def write_to_health_file(self):
        status_time_unix_nano = time.time_ns()
        health_file_location = os.environ.get(
            "NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", "file:///newrelic/apm/health"
        )

        # Additional safeguard though health delivery location contents were initially checked to determine if health
        # check should be enabled
        if not health_file_location:
            return

        try:
            file_path = urlparse(health_file_location).path
            file_id = self.get_file_id()
            file_name = f"health-{file_id}.yml"
            full_path = os.path.join(file_path, file_name)
            is_healthy = self.is_healthy

            with open(full_path, "w") as f:
                f.write(f"healthy: {is_healthy}\n")
                f.write(f"status: {self.status_message}\n")
                f.write(f"start_time_unix_nano: {self.start_time_unix_nano}\n")
                f.write(f"status_time_unix_nano: {status_time_unix_nano}\n")
                if not is_healthy:
                    f.write(f"last_error: NR-APM-{self.status_code:03d}\n")
        except Exception:
            _logger.warning("Unable to write to agent health file.")

    def get_file_id(self):
        pid = os.getpid()

        # Each file name should have a UUID with hyphens stripped appended to it
        file_id = str(uuid.uuid4()).replace("-", "")

        # Map the UUID to the process ID to ensure each agent instance has one UUID associated with it
        if pid not in self.pid_file_id_map:
            self.pid_file_id_map[pid] = file_id
            return file_id

        return self.pid_file_id_map[pid]


def agent_control_health_instance():
    # Helper function directly returns the singleton instance similar to agent_instance()
    return AgentControlHealth.agent_control_health_singleton()


def agent_control_healthcheck_loop():
    try:
        reporting_frequency = int(os.environ.get("NEW_RELIC_AGENT_CONTROL_HEALTH_FREQUENCY", 5))
        # If we have an invalid integer value for frequency, default back to 5
        if reporting_frequency <= 0:
            reporting_frequency = 5
    except Exception:
        # If we run into an exception when int typecasting, default back to 5
        reporting_frequency = 5

    scheduler = sched.scheduler(time.time, time.sleep)

    # Target this function when starting agent control health check threads to keep the scheduler running
    scheduler.enter(reporting_frequency, 1, agent_control_healthcheck, (scheduler, reporting_frequency))
    scheduler.run()


def agent_control_healthcheck(scheduler, reporting_frequency):
    scheduler.enter(reporting_frequency, 1, agent_control_healthcheck, (scheduler, reporting_frequency))

    agent_control_health_instance().write_to_health_file()
