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

from _test_agents import MANAGER_NAME, agent_event
from conftest import AGENT_NAME, EXPECTED_VERSION_METRICS
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

WORKER_NAME = f"{AGENT_NAME}_0"

EXPECTED_MANAGER_METRIC = (f"Llm/agent/CrewAI/crewai.agent.core:Agent.execute_task/{MANAGER_NAME}", 1)
EXPECTED_WORKER_METRIC = (f"Llm/agent/CrewAI/crewai.agent.core:Agent.execute_task/{WORKER_NAME}", 1)


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events([agent_event(name=WORKER_NAME), agent_event(name=MANAGER_NAME)])
@validate_transaction_metrics(
    "test_crew_hierarchical:test_crew_hierarchical",
    scoped_metrics=[EXPECTED_MANAGER_METRIC, EXPECTED_WORKER_METRIC],
    rollup_metrics=[EXPECTED_MANAGER_METRIC, EXPECTED_WORKER_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_crew_hierarchical(build_hierarchical_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_hierarchical_crew(crewai_llm, num_agents=1)
    result = crew.kickoff()
    assert str(result)
