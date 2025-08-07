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
import sys
import threading
import time
import uuid
from enum import IntEnum
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from newrelic.core.config import _environ_as_bool, _environ_as_int

_logger = logging.getLogger(__name__)


class HealthStatus(IntEnum):
    HEALTHY = 0
    INVALID_LICENSE = 1
    MISSING_LICENSE = 2
    FORCED_DISCONNECT = 3
    HTTP_ERROR = 4
    MAX_APP_NAME = 6
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
    HealthStatus.MAX_APP_NAME.value: "The maximum number of configured app names (3) exceeded",
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

NR_CONNECTION_ERROR_CODES = frozenset([HealthStatus.FAILED_NR_CONNECTION.value, HealthStatus.FORCED_DISCONNECT.value])


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
        self._health_delivery_location_cache = {}

    @property
    def health_check_enabled(self):
        # Default to False - this must be explicitly set to True by the sidecar/ operator to enable health check
        agent_control_enabled = _environ_as_bool("NEW_RELIC_AGENT_CONTROL_ENABLED", False)
        if not agent_control_enabled:
            return False

        return self.health_delivery_location_is_valid

    @property
    def health_delivery_location(self):
        file_uri = (
            os.environ.get("NEW_RELIC_AGENT_CONTROL_HEALTH_DELIVERY_LOCATION", "") or "file:///newrelic/apm/health"
        )

        # Return from cache if already parsed
        if file_uri in self._health_delivery_location_cache:
            return self._health_delivery_location_cache[file_uri]

        # Parse and add to cache
        path = self.parse_health_delivery_location(file_uri)
        if path is not None:
            self._health_delivery_location_cache[file_uri] = path

        return path

    @property
    def health_delivery_location_is_valid(self):
        # Verify whether file directory provided to agent via env var is a valid file URI to determine whether health
        # check should run
        try:
            path = self.health_delivery_location
            if path is None:
                # Warning already logged in parse_health_delivery_location()
                return False

            # Check if the path exists
            if not path.exists():
                _logger.warning(
                    "Configured Agent Control health delivery location does not exist. Health check will not be enabled."
                )
                return False

            return True

        except Exception:
            _logger.warning(
                "Configured Agent Control health delivery location is not valid. Health check will not be enabled."
            )
            return False

    @classmethod
    def parse_health_delivery_location(cls, file_uri):
        """Parse the health delivery location and return it as a Path object."""

        # No built in method to correctly parse file URI to a path on Python < 3.13.
        # In the future, Path.from_uri() can be used directly.

        # For now, parse with urllib.parse.urlparse and convert to a Path object.
        parsed_uri = urlparse(file_uri)

        # Ensure URI has at least a scheme and path
        if not parsed_uri.scheme or not parsed_uri.path:
            _logger.warning(
                "Configured Agent Control health delivery location is not a complete file URI. Health check will not be enabled."
            )
            return None

        # Ensure URI has a file scheme
        if parsed_uri.scheme != "file":
            _logger.warning(
                "Configured Agent Control health delivery location does not have a valid scheme. Health check will not be enabled."
            )
            return None

        # Handle Windows systems carefully due to inconsistent path handling
        if sys.platform == "win32":
            if parsed_uri.netloc:
                # Matching behavior of pip where netloc is prepended with a double backslash
                # https://github.com/pypa/pip/blob/022248f6484fe87dc0ef5aec3437f4c7971fd14b/pip/download.py#L442
                urlpathname = url2pathname(rf"\\\\{parsed_uri.netloc}{parsed_uri.path}")
                return Path(urlpathname)
            else:
                # If there's no netloc, we use url2pathname to fix leading slashes
                return Path(url2pathname(parsed_uri.path))
        else:
            # On non-Windows systems we can use the parsed path directly
            return Path(parsed_uri.path)

    @property
    def is_healthy(self):
        return self.status_code == HealthStatus.HEALTHY.value

    def set_health_status(self, status_code, response_code=None, info=None):
        previous_status_code = self.status_code

        if status_code == HealthStatus.FAILED_NR_CONNECTION.value and previous_status_code in LICENSE_KEY_ERROR_CODES:
            # Do not update to failed connection status when license key is the issue so the more descriptive status is not overridden
            return
        elif status_code in NR_CONNECTION_ERROR_CODES and previous_status_code == HealthStatus.MAX_APP_NAME:
            # Do not let NR connection error override the max app name status
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

        try:
            health_dir_path = self.health_delivery_location
            if health_dir_path is None:
                # Allow except block to handle logging a warning
                raise ValueError("Health delivery location is not valid.")

            file_id = self.get_file_id()
            health_file_path = health_dir_path / f"health-{file_id}.yml"
            is_healthy = self.is_healthy  # Cache property value to avoid multiple calls

            with health_file_path.open("w") as f:
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
    reporting_frequency = _environ_as_int("NEW_RELIC_AGENT_CONTROL_HEALTH_FREQUENCY", 5)
    # If we have an invalid integer value for frequency, default back to 5
    if reporting_frequency <= 0:
        reporting_frequency = 5

    scheduler = sched.scheduler(time.time, time.sleep)

    # Target this function when starting agent control health check threads to keep the scheduler running
    scheduler.enter(reporting_frequency, 1, agent_control_healthcheck, (scheduler, reporting_frequency))
    scheduler.run()


def agent_control_healthcheck(scheduler, reporting_frequency):
    scheduler.enter(reporting_frequency, 1, agent_control_healthcheck, (scheduler, reporting_frequency))

    agent_control_health_instance().write_to_health_file()
