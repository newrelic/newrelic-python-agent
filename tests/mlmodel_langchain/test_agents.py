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
from langchain.tools import tool
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_with_context_attrs,
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

PROMPT = {"messages": [HumanMessage('Use a tool to add an exclamation to the word "Hello"')]}
ERROR_PROMPT = {"messages": [HumanMessage('Use a tool to add an exclamation to the word "exc"')]}

agent_recorded_event = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "langchain",
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
            "vendor": "langchain",
            "ingest_source": "Python",
            "error": True,
            "duration": None,
        },
    )
]


@tool
def add_exclamation(message: str) -> str:
    """Adds an exclamation mark to the input message."""
    if "exc" in message:
        raise RuntimeError("Oops")
    return f"{message}!"


@reset_core_stats_engine()
# @validate_custom_events(events_with_context_attrs(agent_recorded_event))
# @validate_custom_event_count(count=2)
# @validate_transaction_metrics(
#     "mlmodel_langchain.test_agents:test_agent",
#     scoped_metrics=[("Llm/agent/LangChain/langchain.agent.agent:Agent.stream_async/my_agent", 1)],
#     rollup_metrics=[("Llm/agent/LangChain/langchain.agent.agent:Agent.stream_async/my_agent", 1)],
#     background_task=True,
# )
# @validate_attributes("agent", ["llm"])
@background_task()
def test_agent(exercise_agent, create_agent_runnable, set_trace_info):
    set_trace_info()
    my_agent = create_agent_runnable(tools=[add_exclamation], system_prompt="You are a text manipulation algorithm.")

    with WithLlmCustomAttributes({"context": "attr"}):
        _response = exercise_agent(my_agent, PROMPT)


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
# @validate_custom_events(agent_recorded_event)
# @validate_custom_event_count(count=2)
# @validate_transaction_metrics(
#     "mlmodel_langchain.test_agents:test_agent_no_content",
#     scoped_metrics=[("Llm/agent/LangChain/langchain.agent.agent:Agent.stream_async/my_agent", 1)],
#     rollup_metrics=[("Llm/agent/LangChain/langchain.agent.agent:Agent.stream_async/my_agent", 1)],
#     background_task=True,
# )
# @validate_attributes("agent", ["llm"])
@background_task()
def test_agent_no_content(exercise_agent, create_agent_runnable, set_trace_info):
    set_trace_info()
    my_agent = create_agent_runnable(tools=[add_exclamation], system_prompt="You are a text manipulation algorithm.")
    _response = exercise_agent(my_agent, PROMPT)


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_agent_outside_txn(exercise_agent, create_agent_runnable):
    my_agent = create_agent_runnable(tools=[add_exclamation], system_prompt="You are a text manipulation algorithm.")
    _response = exercise_agent(my_agent, PROMPT)


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_agent_disabled_ai_monitoring_events(exercise_agent, create_agent_runnable, set_trace_info):
    set_trace_info()
    my_agent = create_agent_runnable(tools=[add_exclamation], system_prompt="You are a text manipulation algorithm.")
    _response = exercise_agent(my_agent, PROMPT)


# @reset_core_stats_engine()
# @validate_transaction_error_event_count(1)
# @validate_error_trace_attributes(callable_name(ValueError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
# @validate_custom_events(agent_recorded_event_error)
# @validate_custom_event_count(count=1)
# @validate_transaction_metrics(
#     "mlmodel_langchain.test_agents:test_agent_execution_error",
#     scoped_metrics=[("Llm/agent/LangChain/langchain.agent.agent:Agent.stream_async/my_agent", 1)],
#     rollup_metrics=[("Llm/agent/LangChain/langchain.agent.agent:Agent.stream_async/my_agent", 1)],
#     background_task=True,
# )
# @validate_attributes("agent", ["llm"])
# @background_task()
# def test_agent_execution_error(exercise_agent, create_agent_runnable, set_trace_info):
#     # Add a wrapper to intentionally force an error in the Agent code
#     raise NotImplementedError

#     # TODO: Find somewhere to inject this in langchain. This was from strands.
#     @transient_function_wrapper("langchain.agent.agent", "Agent._convert_prompt_to_messages")
#     def _wrap_convert_prompt_to_messages(wrapped, instance, args, kwargs):
#         raise ValueError("Oops")

#     @_wrap_convert_prompt_to_messages
#     def _test():
#         set_trace_info()
#         my_agent = create_agent_runnable(
#             tools=[add_exclamation], system_prompt="You are a text manipulation algorithm."
#         )
#         exercise_agent(my_agent, PROMPT)  # raises ValueError

#     with pytest.raises(ValueError):
#         _test()  # No output to validate
