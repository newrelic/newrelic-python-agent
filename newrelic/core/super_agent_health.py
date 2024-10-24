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
import threading
import time
from pathlib import Path, PurePath
from urllib.parse import urlparse
import sched

_logger = logging.getLogger(__name__)


HEALTH_CHECK_STATUSES = {
    "healthy": ("NR-APM-000", "Healthy"),
    "invalid_license": ("NR-APM-001", "Invalid license key (HTTP status code 401)"),
    "missing_license": ("NR-APM-002", "License key missing in configuration"),
    "forced_disconnect": ("NR-APM-003", "Forced disconnect received from New Relic (HTTP status code 410)"),
    "http_error": ("NR-APM-004", "HTTP error response code received from New Relic"),
    "max_app_names": ("NR-APM-006", "The maximum number of configured app names (3) exceeded"),
    "proxy_error": ("NR-APM-007", "HTTP Proxy configuration error"),
    "agent_disabled": ("NR-APM-008", "Agent is disabled via configuration"),
    "agent_shutdown": ("NR-APM-099", "Agent has shutdown"),
}

HEALTH_FILE_LOCATION = os.environ.get("NEW_RELIC_SUPERAGENT_HEALTH_DELIVERY_LOCATION", None)
PARSED_URI = urlparse(HEALTH_FILE_LOCATION)


class SuperAgentHealth():
    _instance_lock = threading.Lock()
    _instance = None

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
        self.agent_start_time = None

    def set_health_status(self, health_status, response_code=None, info=None):
        last_error, current_status = HEALTH_CHECK_STATUSES[health_status]

        if health_status == "http_error" and response_code and info:
            current_status = (
                f"HTTP error response code {response_code} received from New Relic while sending data type {info}"
            )

        if health_status == "proxy_error" and response_code:
            current_status = f"HTTP Proxy configuration error; response code {response_code}"

        if health_status == "agent_shutdown" and self.status != "Healthy":
            pass

        else:
            self.last_error = last_error
            self.status = current_status

    def write_to_health_file(self):
        is_healthy = True if self.status == "Healthy" else False
        status_time_unix_nano = time.time_ns()

        file_path = urlparse(HEALTH_FILE_LOCATION).path
        pid = os.getpid()
        file_name = f"health_{pid}.yml"
        full_path = os.path.join(file_path, file_name)

        try:
            with open(full_path, "w") as f:
                f.write(f"healthy: {is_healthy}\n")
                f.write(f"status: {self.status}\n")
                f.write(f"start_time_unix_nano: {self.start_time_unix_nano}\n")
                f.write(f"status_time_unix_nano: {status_time_unix_nano}\n")
                f.write(f"last_error: {self.last_error}\n")
        except:
            _logger.warning("Unable to write agent health.")


def super_agent_health_instance():
    return SuperAgentHealth.super_agent_health_singleton()


def super_agent_healthcheck_loop():
    reporting_frequency = os.environ.get("NEW_RELIC_SUPERAGENT_HEALTH_FREQUENCY", 5)
    scheduler = sched.scheduler(time.time, time.sleep)

    scheduler.enter(reporting_frequency, 1, super_agent_healthcheck, (scheduler, reporting_frequency))
    scheduler.run()


def super_agent_healthcheck(scheduler, reporting_frequency):
    scheduler.enter(reporting_frequency, 1, super_agent_healthcheck, (scheduler, reporting_frequency))

    super_agent_health_instance().write_to_health_file()

# class SuperAgentHealthCheck:
#     _last_error = "NR-APM-000"
#     _status = "Healthy"
#     _start_time_unix_nano = None
#
#     def __init__(self):
#         pass
#
#     @classmethod
#     def set_health_status(cls, health_status, response_code=None, info=None):
#         last_error, current_status = HEALTH_CHECK_STATUSES[health_status]
#
#         if health_status == "http_error" and response_code and info:
#             current_status = (
#                 f"HTTP error response code {response_code} received from New Relic while sending data type {info}"
#             )
#
#         if health_status == "proxy_error" and response_code:
#             current_status = f"HTTP Proxy configuration error; response code {response_code}"
#
#         if health_status == "agent_shutdown" and cls._status != "Healthy":
#             pass
#
#         else:
#             cls._last_error = last_error
#             cls._status = current_status
#
#     @classmethod
#     def set_agent_start_time(cls, agent_start_time):
#         cls._start_time_unix_nano = agent_start_time
#
#     @classmethod
#     def write_to_health_file(cls):
#         is_healthy = True if cls._status == "Healthy" else False
#         status_time_unix_nano = time.time_ns()
#         file_path = urlparse(HEALTH_FILE_LOCATION).path
#
#         with open(file_path, "w") as f:
#             f.write(f"healthy: {is_healthy}\n")
#             f.write(f"status: {cls._status}\n")
#             f.write(f"start_time_unix_nano: {cls._start_time_unix_nano}\n")
#             f.write(f"status_time_unix_nano: {status_time_unix_nano}\n")
#             f.write(f"last_error: {cls._last_error}\n")
#
#

def is_valid_file_delivery_location(file_uri):
    if not file_uri:
        _logger.warning(
            "Configured Super Agent health delivery location is empty. Super Agent health check will not be enabled."
        )
        return False

    try:
        parsed_uri = urlparse(file_uri)

        if not parsed_uri.scheme or not parsed_uri.path:
            _logger.warning(
                "Configured Super Agent health delivery location is not a complete file URI. Super Agent health check will not be enabled."
            )
            return False

        if parsed_uri.scheme != "file":
            _logger.warning(
                "Configured Super Agent health delivery location does not have a valid scheme. Super Agent health check will not be enabled."
            )
            return False

        path = Path(parsed_uri.path)

        # Check if the path exists
        if not path.parent.exists():
            _logger.warning(
                "Configured Super Agent health delivery location does not exist. Super Agent health check will not be enabled."
            )
            return False

        return True

    except Exception as e:
        _logger.warning(
            "Configured Super Agent health delivery location is not valid. Super Agent health check will not be enabled."
        )
        return False
