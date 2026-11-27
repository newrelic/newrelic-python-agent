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
from _test_agents import agent_event
from conftest import AGENT_NAME, AGENT_PROMPT, EXPECTED_VERSION_METRICS
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import disabled_ai_monitoring_settings
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import transient_function_wrapper

ERROR_MESSAGE = "intentional agent failure"

EXPECTED_AGENT_METRIC = (f"Llm/agent/CrewAI/crewai.agent.core:Agent.execute_task/{AGENT_NAME}", 1)

# 1 event with error=True, for the agent's execute_task() call
EXPECTED_EVENT_COUNT = 1


@transient_function_wrapper("crewai.agent.core", "Agent._execute_without_timeout")
def inject_agent_error(wrapped, instance, args, kwargs):
    raise ValueError(ERROR_MESSAGE)


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(callable_name(ValueError))
@validate_custom_events([agent_event(error=True)])
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_agent_error:test_agent_execute_task_error",
    scoped_metrics=[EXPECTED_AGENT_METRIC],
    rollup_metrics=[EXPECTED_AGENT_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
@inject_agent_error
def test_agent_execute_task_error(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, description=AGENT_PROMPT, max_retry_limit=0)
    with pytest.raises(ValueError):
        crew.kickoff()


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@validate_transaction_metrics("test_agent_error:test_agent_error_disabled_ai_monitoring", background_task=True)
@background_task()
@inject_agent_error
def test_agent_error_disabled_ai_monitoring(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, description=AGENT_PROMPT, max_retry_limit=0)
    with pytest.raises(ValueError):
        crew.kickoff()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@inject_agent_error
def test_agent_error_outside_transaction(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, description=AGENT_PROMPT, max_retry_limit=0)
    with pytest.raises(ValueError):
        crew.kickoff()
