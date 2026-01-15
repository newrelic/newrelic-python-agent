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
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture
from testing_support.ml_testing_utils import set_trace_info

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
    app_name="Python Agent Test (mlmodel_strands)", default_settings=_default_settings
)


@pytest.fixture(scope="session", params=["invoke", "invoke_async", "stream_async"])
def exercise_agent(request, loop):
    def _exercise_agent(agent, prompt):
        if request.param == "invoke":
            return agent(prompt)
        elif request.param == "invoke_async":
            return loop.run_until_complete(agent.invoke_async(prompt))
        elif request.param == "stream_async":

            async def _exercise_agen():
                return [event async for event in agent.stream_async(prompt)]

            return loop.run_until_complete(_exercise_agen())
        else:
            raise NotImplementedError

    return _exercise_agent
