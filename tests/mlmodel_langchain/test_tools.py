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
from langchain.messages import HumanMessage
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    events_with_context_attrs,
    tool_events_sans_content,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_error_event_count import validate_transaction_error_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import transient_function_wrapper

from ._test_tools import add_exclamation, tool_method_name, tool_type

PROMPT = {"messages": [HumanMessage('Use a tool to add an exclamation to the word "Hello"')]}
ERROR_PROMPT = {"messages": [HumanMessage('Use a tool to add an exclamation to the word "exc"')]}
SYNC_METHODS = {"invoke", "stream"}

tool_recorded_event = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": None,
            "output": "Hello!",
            "name": "add_exclamation",
            "agent_name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'message': 'Hello'}",
            "vendor": "langchain",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]

tool_recorded_event_execution_error = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": None,
            "name": "add_exclamation",
            "agent_name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'message': 'exc'}",
            "vendor": "langchain",
            "ingest_source": "Python",
            "error": True,
            "duration": None,
        },
    )
]

tool_recorded_event_forced_internal_error = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": None,
            "name": "add_exclamation",
            "agent_name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'message': 'Hello'}",
            "vendor": "langchain",
            "ingest_source": "Python",
            "duration": None,
            "error": True,
        },
    )
]


@dt_enabled
@reset_core_stats_engine()
def test_tool(exercise_agent, set_trace_info, create_agent_runnable, add_exclamation, tool_method_name):
    @validate_custom_events(events_with_context_attrs(tool_recorded_event))
    @validate_custom_event_count(count=exercise_agent._expected_event_count)
    @validate_transaction_metrics(
        "test_tool",
        scoped_metrics=[(f"Llm/tool/LangChain/{tool_method_name}/add_exclamation", 1)],
        rollup_metrics=[(f"Llm/tool/LangChain/{tool_method_name}/add_exclamation", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
    @validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
    @background_task(name="test_tool")
    def _test():
        set_trace_info()
        my_agent = create_agent_runnable(
            tools=[add_exclamation], system_prompt="You are a text manipulation algorithm."
        )

        with WithLlmCustomAttributes({"context": "attr"}):
            exercise_agent(my_agent, PROMPT)

    _test()


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_tool_no_content(exercise_agent, set_trace_info, create_agent_runnable, add_exclamation, tool_method_name):
    @validate_custom_events(tool_events_sans_content(tool_recorded_event))
    @validate_custom_event_count(count=exercise_agent._expected_event_count)
    @validate_transaction_metrics(
        "test_tool_no_content",
        scoped_metrics=[(f"Llm/tool/LangChain/{tool_method_name}/add_exclamation", 1)],
        rollup_metrics=[(f"Llm/tool/LangChain/{tool_method_name}/add_exclamation", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
    @validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
    @background_task(name="test_tool_no_content")
    def _test():
        set_trace_info()
        my_agent = create_agent_runnable(
            tools=[add_exclamation], system_prompt="You are a text manipulation algorithm."
        )
        exercise_agent(my_agent, PROMPT)

    _test()


@dt_enabled
@reset_core_stats_engine()
def test_tool_execution_error(exercise_agent, set_trace_info, create_agent_runnable, add_exclamation, tool_method_name):
    @validate_transaction_error_event_count(1)
    @validate_error_trace_attributes(
        callable_name(RuntimeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
    )
    @validate_custom_events(tool_recorded_event_execution_error)
    @validate_custom_event_count(exercise_agent._expected_event_count_error)
    @validate_transaction_metrics(
        "test_tool_execution_error",
        scoped_metrics=[(f"Llm/tool/LangChain/{tool_method_name}/add_exclamation", 1)],
        rollup_metrics=[(f"Llm/tool/LangChain/{tool_method_name}/add_exclamation", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
    @validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
    @background_task(name="test_tool_execution_error")
    def _test():
        set_trace_info()
        my_agent = create_agent_runnable(
            tools=[add_exclamation], system_prompt="You are a text manipulation algorithm."
        )
        with pytest.raises(RuntimeError):
            exercise_agent(my_agent, ERROR_PROMPT)

    _test()


@dt_enabled
@reset_core_stats_engine()
def test_tool_pre_execution_exception(
    exercise_agent, set_trace_info, create_agent_runnable, add_exclamation, tool_method_name
):
    # Add a wrapper to intentionally force an error in the setup logic of BaseTool
    @transient_function_wrapper("langchain_core.tools.base", "BaseTool._parse_input")
    def inject_exception(wrapped, instance, args, kwargs):
        raise ValueError("Oops")

    @inject_exception
    @validate_transaction_error_event_count(1)
    @validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
    @validate_custom_events(tool_recorded_event_forced_internal_error)
    @validate_custom_event_count(exercise_agent._expected_event_count_error)
    @validate_transaction_metrics(
        "test_tool_pre_execution_exception",
        scoped_metrics=[(f"Llm/tool/LangChain/{tool_method_name}/add_exclamation", 1)],
        rollup_metrics=[(f"Llm/tool/LangChain/{tool_method_name}/add_exclamation", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
    @validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
    @background_task(name="test_tool_pre_execution_exception")
    def _test():
        set_trace_info()
        my_agent = create_agent_runnable(
            tools=[add_exclamation], system_prompt="You are a text manipulation algorithm."
        )
        with pytest.raises(ValueError):
            exercise_agent(my_agent, PROMPT)

    _test()
