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
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixture.vcr import *  # noqa: F403
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture
from testing_support.ml_testing_utils import set_trace_info

from newrelic.common.package_version_utils import get_package_version, get_package_version_tuple

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slowdowns.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "ai_monitoring.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_agentframework)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_agentframework)"],
)


AGENT_FRAMEWORK_VERSION_TUPLE = get_package_version_tuple("agent-framework")
AGENT_FRAMEWORK_VERSION = get_package_version("agent-framework")
assert AGENT_FRAMEWORK_VERSION, "Failed to pull agent-framework version for supportability metric"


@pytest.fixture
def exercise_agent(loop):
    def _exercise_agent(agent, prompt):
        return loop.run_until_complete(agent.run(prompt))

    return _exercise_agent
