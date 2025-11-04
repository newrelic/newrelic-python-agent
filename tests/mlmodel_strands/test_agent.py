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
from strands import Agent, tool
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_with_context_attrs,
    tool_events_sans_content,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_transaction_error_event_count import validate_transaction_error_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import transient_function_wrapper

tool_recorded_event = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": "123",
            "output": "{'text': 'Hello!'}",
            "name": "add_exclamation",
            "agent_name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'message': 'Hello'}",
            "vendor": "strands",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]

tool_recorded_event_forced_internal_error = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": "123",
            "name": "add_exclamation",
            "agent_name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'message': 'Hello'}",
            "vendor": "strands",
            "ingest_source": "Python",
            "duration": None,
            "error": True,
        },
    )
]

tool_recorded_event_error_coro = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": "123",
            "name": "throw_exception_coro",
            "agent_name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'message': 'Hello'}",
            "vendor": "strands",
            "ingest_source": "Python",
            "error": True,
            "output": "{'text': 'Error: RuntimeError - Oops'}",
            "duration": None,
        },
    )
]


tool_recorded_event_error_agen = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": "123",
            "name": "throw_exception_agen",
            "agent_name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'message': 'Hello'}",
            "vendor": "strands",
            "ingest_source": "Python",
            "error": True,
            "output": "{'text': 'Error: RuntimeError - Oops'}",
            "duration": None,
        },
    )
]


agent_recorded_event = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "strands",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]

agent_recorded_event_error = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "strands",
            "ingest_source": "Python",
            "error": True,
            "duration": None,
        },
    )
]


# Example tool for testing purposes
@tool
async def add_exclamation(message: str) -> str:
    return f"{message}!"


@tool
async def throw_exception_coro(message: str) -> str:
    raise RuntimeError("Oops")


@tool
async def throw_exception_agen(message: str) -> str:
    raise RuntimeError("Oops")
    yield


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(tool_recorded_event))
@validate_custom_events(events_with_context_attrs(agent_recorded_event))
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_agent:test_agent_invoke",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_agent_invoke(set_trace_info, single_tool_model):
    set_trace_info()
    my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])

    with WithLlmCustomAttributes({"context": "attr"}):
        response = my_agent('Add an exclamation to the word "Hello"')
    assert response.message["content"][0]["text"] == "Success!"
    assert response.metrics.tool_metrics["add_exclamation"].success_count == 1


@reset_core_stats_engine()
@validate_custom_events(tool_recorded_event)
@validate_custom_events(agent_recorded_event)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_agent:test_agent_invoke_async",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_agent_invoke_async(loop, set_trace_info, single_tool_model):
    set_trace_info()
    my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])

    async def _test():
        response = await my_agent.invoke_async('Add an exclamation to the word "Hello"')
        assert response.message["content"][0]["text"] == "Success!"
        assert response.metrics.tool_metrics["add_exclamation"].success_count == 1

    loop.run_until_complete(_test())


@reset_core_stats_engine()
@validate_custom_events(tool_recorded_event)
@validate_custom_events(agent_recorded_event)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_agent:test_agent_stream_async",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_agent_stream_async(loop, set_trace_info, single_tool_model):
    set_trace_info()
    my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])

    async def _test():
        response = my_agent.stream_async('Add an exclamation to the word "Hello"')
        messages = [event["message"]["content"] async for event in response if "message" in event]

        assert len(messages) == 3
        assert messages[0][0]["text"] == "Calling add_exclamation tool"
        assert messages[0][1]["toolUse"]["name"] == "add_exclamation"
        assert messages[1][0]["toolResult"]["content"][0]["text"] == "Hello!"
        assert messages[2][0]["text"] == "Success!"

    loop.run_until_complete(_test())


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(agent_recorded_event)
@validate_custom_events(tool_events_sans_content(tool_recorded_event))
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_agent:test_agent_invoke_no_content",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_agent_invoke_no_content(set_trace_info, single_tool_model):
    set_trace_info()
    my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])

    response = my_agent('Add an exclamation to the word "Hello"')
    assert response.message["content"][0]["text"] == "Success!"
    assert response.metrics.tool_metrics["add_exclamation"].success_count == 1


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_agent_invoke_disabled_ai_monitoring_events(set_trace_info, single_tool_model):
    set_trace_info()
    my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])

    response = my_agent('Add an exclamation to the word "Hello"')
    assert response.message["content"][0]["text"] == "Success!"
    assert response.metrics.tool_metrics["add_exclamation"].success_count == 1


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(agent_recorded_event_error)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    "test_agent:test_agent_invoke_error",
    scoped_metrics=[("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1)],
    rollup_metrics=[("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_agent_invoke_error(set_trace_info, single_tool_model):
    # Add a wrapper to intentionally force an error in the Agent code
    @transient_function_wrapper("strands.agent.agent", "Agent._convert_prompt_to_messages")
    def _wrap_convert_prompt_to_messages(wrapped, instance, args, kwargs):
        raise ValueError("Oops")

    @_wrap_convert_prompt_to_messages
    def _test():
        set_trace_info()
        my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])
        my_agent('Add an exclamation to the word "Hello"')  # raises ValueError

    with pytest.raises(ValueError):
        _test()


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(RuntimeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(tool_recorded_event_error_coro)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_agent:test_agent_invoke_tool_coro_runtime_error",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/throw_exception_coro", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/throw_exception_coro", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_agent_invoke_tool_coro_runtime_error(set_trace_info, single_tool_model_runtime_error_coro):
    set_trace_info()
    my_agent = Agent(name="my_agent", model=single_tool_model_runtime_error_coro, tools=[throw_exception_coro])

    response = my_agent('Add an exclamation to the word "Hello"')
    assert response.message["content"][0]["text"] == "Success!"
    assert response.metrics.tool_metrics["throw_exception_coro"].error_count == 1


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(RuntimeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(tool_recorded_event_error_agen)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_agent:test_agent_invoke_tool_agen_runtime_error",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/throw_exception_agen", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/throw_exception_agen", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_agent_invoke_tool_agen_runtime_error(set_trace_info, single_tool_model_runtime_error_agen):
    set_trace_info()
    my_agent = Agent(name="my_agent", model=single_tool_model_runtime_error_agen, tools=[throw_exception_agen])

    response = my_agent('Add an exclamation to the word "Hello"')
    assert response.message["content"][0]["text"] == "Success!"
    assert response.metrics.tool_metrics["throw_exception_agen"].error_count == 1


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(agent_recorded_event)
@validate_custom_events(tool_recorded_event_forced_internal_error)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_agent:test_agent_tool_forced_exception",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/my_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/add_exclamation", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_agent_tool_forced_exception(set_trace_info, single_tool_model):
    # Add a wrapper to intentionally force an error in the ToolExecutor._stream code to hit the exception path in
    # the AsyncGeneratorProxy
    @transient_function_wrapper("strands.hooks.events", "BeforeToolCallEvent.__init__")
    def _wrap_BeforeToolCallEvent_init(wrapped, instance, args, kwargs):
        raise ValueError("Oops")

    @_wrap_BeforeToolCallEvent_init
    def _test():
        set_trace_info()
        my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])
        my_agent('Add an exclamation to the word "Hello"')

    # This will not explicitly raise a ValueError when running the test but we are still able to  capture it in the error trace
    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_agent_invoke_outside_txn(single_tool_model):
    my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])

    response = my_agent('Add an exclamation to the word "Hello"')
    assert response.message["content"][0]["text"] == "Success!"
    assert response.metrics.tool_metrics["add_exclamation"].success_count == 1
