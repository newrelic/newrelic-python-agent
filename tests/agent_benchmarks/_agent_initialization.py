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
import sys
from pathlib import Path
from threading import Lock

# Amend sys.path to allow importing fixtures from testing_support
tests_path = Path(__file__).parent.parent
sys.path.append(str(tests_path))

from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture  # noqa: E402

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

_collector_agent_registration_fixture = collector_agent_registration_fixture(
    app_name="Python Agent Test (benchmarks)", default_settings=_default_settings
)

INITIALIZATION_LOCK = Lock()
APPLICATIONS = []

DISALLOWED_ENV_VARS = ("NEW_RELIC_CONFIG_FILE", "NEW_RELIC_LICENSE_KEY")


def collector_agent_registration(instance):
    # If the application is already registered, exit early
    if APPLICATIONS:
        instance.application = APPLICATIONS[0]  # Make application accessible to benchmarks
        return

    # Register the agent with the collector using the pytest fixture manually
    with INITIALIZATION_LOCK:
        if APPLICATIONS:  # Must re-check this condition just in case
            instance.application = APPLICATIONS[0]  # Make application accessible to benchmarks
            return

        # Force benchmarking to always use developer mode
        os.environ["NEW_RELIC_DEVELOPER_MODE"] = "true"  # Force developer mode
        for env_var in DISALLOWED_ENV_VARS:  # Drop disallowed env vars
            os.environ.pop(env_var, None)

        # Use pytest fixture by hand to start the agent
        fixture = _collector_agent_registration_fixture()
        APPLICATIONS.append(next(fixture))

        # Wait for the application to become active
        collector_available_fixture(APPLICATIONS[0])

        # Make application accessible to benchmarks
        instance.application = APPLICATIONS[0]
