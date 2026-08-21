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
from _test_tools import TOOL_NAME, get_capital, tool_recorded_event_error
from conftest import EXPECTED_VERSION_METRICS, TOOL_PROMPT
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_error_event_count import validate_transaction_error_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import transient_function_wrapper

EXPECTED_SYNC_TOOL_METRIC = (f"Llm/tool/CrewAI/crewai.tools.tool_usage:ToolUsage._use/{TOOL_NAME}", 1)
EXPECTED_ASYNC_TOOL_METRIC = (f"Llm/tool/CrewAI/crewai.tools.tool_usage:ToolUsage._ause/{TOOL_NAME}", 1)

# 5 events:
#  * 1 LlmTool
#  * 1 LlmChatCompletionSummary -- the injected failure aborts the run after one round-trip
#  * 3 LlmChatCompletionMessage from that round-trip
EXPECTED_EVENT_COUNT = 5


class CrewAIToolError(RuntimeError):
    pass


@transient_function_wrapper("crewai.tools.tool_usage", "ToolUsage._check_tool_repeated_usage")
def inject_tool_error(wrapped, instance, args, kwargs):
    raise CrewAIToolError("Oops")


@dt_enabled
@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(CrewAIToolError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(tool_recorded_event_error(record_content=True))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_tool_error:test_tool_error",
    scoped_metrics=[EXPECTED_SYNC_TOOL_METRIC],
    rollup_metrics=[EXPECTED_SYNC_TOOL_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": f'{{"type": "APM-AI_TOOL", "name": "{TOOL_NAME}"}}'})
@inject_tool_error
@background_task()
def test_tool_error(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, tools=[get_capital], description=TOOL_PROMPT, max_retry_limit=0)
    with pytest.raises(CrewAIToolError):
        crew.kickoff()


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(CrewAIToolError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(tool_recorded_event_error(record_content=False))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_tool_error:test_tool_error_no_content",
    scoped_metrics=[EXPECTED_SYNC_TOOL_METRIC],
    rollup_metrics=[EXPECTED_SYNC_TOOL_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@inject_tool_error
@background_task()
def test_tool_error_no_content(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, tools=[get_capital], description=TOOL_PROMPT, max_retry_limit=0)
    with pytest.raises(CrewAIToolError):
        crew.kickoff()


@dt_enabled
@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(CrewAIToolError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(tool_recorded_event_error(record_content=True))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_tool_error:test_tool_error_async",
    scoped_metrics=[EXPECTED_ASYNC_TOOL_METRIC],
    rollup_metrics=[EXPECTED_ASYNC_TOOL_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": f'{{"type": "APM-AI_TOOL", "name": "{TOOL_NAME}"}}'})
@inject_tool_error
@background_task()
def test_tool_error_async(build_crew, crewai_llm, set_trace_info, loop):
    set_trace_info()
    crew = build_crew(crewai_llm, tools=[get_capital], description=TOOL_PROMPT, max_retry_limit=0)
    with pytest.raises(CrewAIToolError):
        loop.run_until_complete(crew.akickoff())


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@validate_transaction_metrics("test_tool_error:test_tool_error_disabled_ai_monitoring", background_task=True)
@inject_tool_error
@background_task()
def test_tool_error_disabled_ai_monitoring(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, tools=[get_capital], description=TOOL_PROMPT, max_retry_limit=0)
    with pytest.raises(CrewAIToolError):
        crew.kickoff()
