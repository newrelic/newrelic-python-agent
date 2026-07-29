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
from _test_agent import AGENT_NAME, PROMPT, agent_recorded_event_error, build_agent
from _test_tools import TOOL_NAME, raising_tool, tool_recorded_event_error
from conftest import EXPECTED_VERSION_METRICS
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_error_event_count import validate_transaction_error_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name

EXPECTED_METRICS = [
    (f"Llm/agent/GoogleADK/run_async/{AGENT_NAME}", 1),
    (f"Llm/tool/GoogleADK/execute_single_function_call_async/{TOOL_NAME}", 1),
]


@dt_enabled
@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(agent_recorded_event_error + tool_recorded_event_error(record_content=True))
# 5 events:
#  * 1 LlmAgent
#  * 1 LlmTool
#  * 3 LLM events from the single Gemini round-trip (Input/Output/Summary)
@validate_custom_event_count(5)
@validate_transaction_metrics(
    "test_tools_error:test_tool_error",
    scoped_metrics=EXPECTED_METRICS,
    rollup_metrics=EXPECTED_METRICS,
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
@validate_span_events(count=1, exact_agents={"subcomponent": f'{{"type": "APM-AI_TOOL", "name": "{TOOL_NAME}"}}'})
@background_task()
def test_tool_error(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent(tools=[raising_tool])
    with pytest.raises(ValueError):
        exercise_agent(agent, PROMPT)
