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

import itertools
import os

import pytest
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.tool import ToolMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixture.vcr import *  # noqa: F403
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
)
from testing_support.ml_testing_utils import set_trace_info

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "ai_monitoring.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_langchain)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_langchain)"],
)

IGNORED_HEADERS.extend(  # noqa: F405
    [
        "X-Stainless-Arch",
        "X-Stainless-Async",
        "X-Stainless-Lang",
        "X-Stainless-OS",
        "X-Stainless-Package-Version",
        "X-Stainless-Raw-Response",
        "X-Stainless-Runtime",
        "X-Stainless-Runtime-Version",
        "x-stainless-retry-count",
        "x-envoy-upstream-service-time",
        "X-Content-Type-Options",
        "x-request-id",
        "x-openai-proxy-wasm",
        "set-cookie",
        "alt-svc",
        "Strict-Transport-Security",
        "Cookie",
    ]
)

# Intercept outgoing requests and log to file for mocking
RECORDED_HEADERS = {"x-request-id", "content-type"}
EXPECTED_AGENT_RESPONSE = "Hello!"
EXPECTED_TOOL_OUTPUT = "Hello!"


@pytest.fixture
def openai_clients(vcr_recording):
    """
    This configures the OpenAI client to use a ReplayApiClient which
    will either record or replay responses depending on the mode.
    """
    from newrelic.core.config import _environ_as_bool

    if vcr_recording:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required.")
    else:
        openai_api_key = os.environ["OPENAI_API_KEY"] = "NOT-A-REAL-SECRET"

    chat = ChatOpenAI(api_key=openai_api_key)
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    return chat, embeddings


@pytest.fixture
def embedding_openai_client(openai_clients):
    _, embedding_client = openai_clients
    return embedding_client


@pytest.fixture
def chat_openai_client(openai_clients):
    chat_client, _ = openai_clients
    return chat_client


def state_function_step(state):
    return {"messages": [f"The real agent said: {state['messages'][-1].content}"]}


def append_function_step(state):
    from langchain.messages import ToolMessage

    if "messages" in state:
        messages = state["messages"]
    elif "model" in state:
        messages = state["model"]["messages"]
    elif "data" in state:
        messages = state["data"]["model"]["messages"]

    messages.append(ToolMessage(f"The real agent said: {messages[-1].content}", tool_call_id=123))
    return state


@pytest.fixture(params=["create_agent", "StateGraph", "RunnableSeq", "RunnableSequence"])
def agent_runnable_type(request):
    return request.param


@pytest.fixture
def create_agent_runnable(agent_runnable_type, chat_openai_client):
    """Create different runnable forms of the same agent and model as a fixture."""

    def _create_agent(model="gpt-5.1", tools=None, system_prompt=None, name="my_agent"):
        from langchain.agents import create_agent

        client = chat_openai_client.with_config(model=model, timeout=30)

        return create_agent(model=client, tools=tools, system_prompt=system_prompt, name=name)

    def _create_state_graph(*args, **kwargs):
        from langgraph.graph import END, START, MessagesState, StateGraph

        agent = _create_agent(*args, **kwargs)

        graph = StateGraph(MessagesState)
        graph.add_node(agent)
        graph.add_node(state_function_step)
        graph.add_edge(START, "my_agent")
        graph.add_edge("my_agent", "state_function_step")
        graph.add_edge("state_function_step", END)

        return graph.compile()

    def _create_runnable_seq(*args, **kwargs):
        from langgraph._internal._runnable import RunnableSeq

        agent = _create_agent(*args, **kwargs)

        return RunnableSeq(agent, append_function_step)

    def _create_runnable_sequence(*args, **kwargs):
        from langchain_core.runnables import RunnableSequence

        agent = _create_agent(*args, **kwargs)

        return RunnableSequence(agent, append_function_step)

    if agent_runnable_type == "create_agent":
        return _create_agent
    elif agent_runnable_type == "StateGraph":
        return _create_state_graph
    elif agent_runnable_type == "RunnableSeq":
        return _create_runnable_seq
    elif agent_runnable_type == "RunnableSequence":
        return _create_runnable_sequence
    else:
        raise NotImplementedError


@pytest.fixture
def validate_agent_output(agent_runnable_type):
    def _unpack_messages(response):
        if isinstance(response, list) and not any(response):
            # Only None are returned from RunnableSeq.stream(), avoid the crash
            return []
        elif isinstance(response, list):
            # stream returns a list of events
            # Messages are packaged into nested dicts with a "model" or "tool_call" key, a "message" key,
            # which contains a list with one or more messages in order. To unpack everything,
            # we need to unpack the dictionaries values and extract the messasges lists, then flatten them.
            try:
                messages_packed = [next(iter(event.values()))["messages"] for event in response]
            except TypeError:
                messages_packed = []
                for event in response:
                    for value in event.values():
                        if isinstance(value, dict):
                            try:
                                dict_content = next(iter(value.values()))
                                if dict_content and ("messages" in dict_content):
                                    messages_packed.append(dict_content["messages"])
                            except StopIteration:
                                pass

            return list(itertools.chain.from_iterable(messages_packed))

        # invoke returns a Response object that contains the messages directly
        return response["messages"]

    def _validate_agent_output(response):
        is_streaming = isinstance(response, list)
        messages = _unpack_messages(response)
        if agent_runnable_type == "create_agent":
            if is_streaming:
                # Events: agent calling tool, tool return value, agent output
                assert len(messages) == 3
                assert messages[0].tool_calls
                assert messages[1].content == EXPECTED_TOOL_OUTPUT
                assert messages[2].content == EXPECTED_AGENT_RESPONSE
            else:
                # Events: input prompt, agent calling tool, tool return value, agent output
                assert len(messages) == 4
                assert messages[1].tool_calls
                assert messages[2].content == EXPECTED_TOOL_OUTPUT
                assert messages[3].content == EXPECTED_AGENT_RESPONSE

        elif agent_runnable_type == "StateGraph":
            # Events: input prompt, agent calling tool, tool return value, agent output, function_step output
            assert len(messages) == 5
            assert messages[1].tool_calls
            assert messages[2].content == EXPECTED_TOOL_OUTPUT
            assert messages[3].content == EXPECTED_AGENT_RESPONSE

        elif agent_runnable_type == "RunnableSeq":
            # stream and astream do not directly output anything for RunnableSeq, and can't be validated.
            if not is_streaming:
                # Events: input prompt, agent calling tool, tool return value, agent output, function_step output
                assert len(messages) == 5
                assert messages[1].tool_calls
                assert messages[2].content == EXPECTED_TOOL_OUTPUT
                assert messages[3].content == EXPECTED_AGENT_RESPONSE

        elif agent_runnable_type == "RunnableSequence":
            if is_streaming:
                # Events: agent output, function_step output
                assert len(messages) == 2
                assert messages[0].content == EXPECTED_AGENT_RESPONSE
            else:
                # Events: input prompt, agent calling tool, tool return value, agent output, function_step output
                assert len(messages) == 5
                assert messages[1].tool_calls
                assert messages[2].content == EXPECTED_TOOL_OUTPUT
                assert messages[3].content == EXPECTED_AGENT_RESPONSE

        else:
            raise NotImplementedError

    return _validate_agent_output


# This is used for `stream_events` and `astream_events`
@pytest.fixture
def validate_agent_event_output(agent_runnable_type):
    def _unpack_messages(response):
        if isinstance(response, list) and not any(response):
            # Only None are returned from RunnableSeq.stream(), avoid the crash
            return []
        elif isinstance(response, list):
            # stream returns a list of events
            # Messages are packaged into nested dicts with a "model" or "tool_call" key, a "message" key,
            # which contains a list with one or more messages in order. To unpack everything,
            # we need to unpack the dictionaries values and extract the messasges lists, then flatten them.
            try:
                messages_packed = [next(iter(event.values()))["messages"] for event in response]
            except TypeError:
                messages_packed = []
                for event in response:
                    for value in event.values():
                        if isinstance(value, dict):
                            try:
                                dict_content = next(iter(value.values()))
                                if dict_content and ("messages" in dict_content):
                                    messages_packed.append(dict_content["messages"])
                            except StopIteration:
                                pass

            return list(itertools.chain.from_iterable(messages_packed))

        # invoke returns a Response object that contains the messages directly
        return response["messages"]

    def _validate_agent_event_output(response):
        messages = _unpack_messages(response)
        if agent_runnable_type == "create_agent":
            for event in messages:
                if isinstance(event, AIMessage) and event.response_metadata["finish_reason"] == "stop":
                    assert event.content == EXPECTED_AGENT_RESPONSE
                elif isinstance(event, AIMessage) and event.response_metadata["finish_reason"] == "tool_calls":
                    assert event.tool_calls
                elif isinstance(event, ToolMessage):
                    assert event.content == EXPECTED_TOOL_OUTPUT

        elif agent_runnable_type == "RunnableSeq":
            # stream and astream do not directly output anything for RunnableSeq, and can't be validated.
            for event in messages:
                if isinstance(event, AIMessage) and event.response_metadata["finish_reason"] == "stop":
                    assert event.content == EXPECTED_AGENT_RESPONSE
                elif isinstance(event, AIMessage) and event.response_metadata["finish_reason"] == "tool_calls":
                    assert event.tool_calls
                elif isinstance(event, ToolMessage):
                    assert event.content == EXPECTED_TOOL_OUTPUT

        elif agent_runnable_type == "StateGraph":
            for event in messages:
                if isinstance(event, AIMessage) and event.response_metadata["finish_reason"] == "stop":
                    assert event.content == EXPECTED_AGENT_RESPONSE
                elif isinstance(event, AIMessage) and event.response_metadata["finish_reason"] == "tool_calls":
                    assert event.tool_calls
                elif isinstance(event, ToolMessage):
                    assert event.content == EXPECTED_TOOL_OUTPUT

        elif agent_runnable_type == "RunnableSequence":
            for event in messages:
                if isinstance(event, AIMessage) and event.response_metadata["finish_reason"] == "stop":
                    assert event.content == EXPECTED_AGENT_RESPONSE
                elif isinstance(event, AIMessage) and event.response_metadata["finish_reason"] == "tool_calls":
                    assert event.tool_calls
                elif isinstance(event, ToolMessage):
                    assert event.content == EXPECTED_TOOL_OUTPUT

        else:
            raise NotImplementedError

    return _validate_agent_event_output


@pytest.fixture(
    params=[
        {"run_method": "invoke", "version": "v1"},
        {"run_method": "invoke", "version": "v2"},
        {"run_method": "ainvoke", "version": "v1"},
        {"run_method": "ainvoke", "version": "v2"},
        {"run_method": "stream", "version": "v1"},
        {"run_method": "stream", "version": "v2"},
        {"run_method": "astream", "version": "v1"},
        {"run_method": "astream", "version": "v2"},
        {"run_method": "astream_events", "version": "v1"},
        {"run_method": "astream_events", "version": "v2"},
    ]
)
def exercise_agent(request, loop, validate_agent_output, validate_agent_event_output, agent_runnable_type):
    def _exercise_agent(agent, prompt):
        if method == "invoke":
            response = agent.invoke(prompt, version=version)
            validate_agent_output(response)
            return response
        elif method == "ainvoke":
            response = loop.run_until_complete(agent.ainvoke(prompt, version=version))
            validate_agent_output(response)
            return response
        elif method == "stream":
            response = list(agent.stream(prompt, version=version))
            validate_agent_output(response)
            return response
        elif method == "astream":

            async def _exercise_agen():
                return [event async for event in agent.astream(prompt, version=version)]

            response = loop.run_until_complete(_exercise_agen())
            validate_agent_output(response)
            return response
        elif method == "astream_events":

            async def _exercise_agen():
                return [event async for event in agent.astream_events(prompt, version=version)]

            response = loop.run_until_complete(_exercise_agen())
            validate_agent_event_output(response)
            return response
        else:
            raise NotImplementedError

    method, version = request.param.get("run_method"), request.param.get("version")
    _exercise_agent._called_method = method  # Used for metric names

    # Expected number of events for a full run of the agent
    if agent_runnable_type != "RunnableSequence":
        _exercise_agent._expected_event_count = 11
        _exercise_agent._expected_event_count_error = 5
    elif method in ("invoke", "ainvoke"):
        _exercise_agent._expected_event_count = 14
        _exercise_agent._expected_event_count_error = 7
    else:
        _exercise_agent._expected_event_count = 13
        _exercise_agent._expected_event_count_error = 7

    return _exercise_agent


@pytest.fixture
def method_name(exercise_agent, agent_runnable_type):
    method = exercise_agent._called_method
    # Only AgentObjectProxy (used for create_agent) instruments `astream_events` directly.
    # For StateGraph/RunnableSeq/RunnableSequence, `astream_events` delegates to `astream`,
    # so the recorded metric is "astream".
    if agent_runnable_type != "create_agent" and method == "astream_events":
        return "astream"
    if agent_runnable_type == "StateGraph":
        return "invoke" if method in ("invoke", "stream", "stream_events") else "ainvoke"
    return method
