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
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events

from newrelic.api.background_task import background_task

from ._test_agents import exercise_method, exercise_method_params, exercise_method_version

CLIENT_PROMPT = {"messages": [HumanMessage("What is the capital of France? Answer in one word.")]}
AGENT_PROMPT = {
    "messages": [
        HumanMessage(
            'Call the add_exclamation tool with message="Hello". Reply with only the tool output, no other text.'
        )
    ]
}


# Agent invocation produces 11 Total Events, 9 from OpenAI and 2 from Langchain
# * Summary, System Prompt, Input Prompt
# * Tool
# * Summary, System Prompt, Input Prompt, Tool Input, Tool Output
# * Agent
AGENT_EVENT_COUNT = 11
CLIENT_EVENT_COUNT = 3  # Summary + Input + Output


# Validations only for the recorded LlmAgent and LlmTool events
agent_recorded_events = [
    [
        {"timestamp": None, "type": "LlmTool"},
        {
            "agent_name": "my_agent",
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "input": "{'message': 'Hello'}",
            "name": "add_exclamation",
            "output": "Hello!",
            "run_id": None,
            "span_id": None,
            "trace_id": None,
            "vendor": "langchain",
        },
    ],
    [
        {"timestamp": None, "type": "LlmAgent"},
        {
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "name": "my_agent",
            "span_id": None,
            "trace_id": None,
            "vendor": "langchain",
        },
    ],
]


@tool
def add_exclamation(message: str) -> str:
    """Adds an exclamation mark to the input message."""
    if "exc" in message:
        raise RuntimeError("Oops")
    return f"{message}!"


def _build_graph(node):
    from langgraph.graph import END, START, MessagesState, StateGraph

    builder = StateGraph(MessagesState)
    builder.add_node("my_agent", node)
    builder.add_edge(START, "my_agent")
    builder.add_edge("my_agent", END)
    return builder.compile()


@pytest.fixture
def create_agent(chat_openai_client):
    def _create_agent(model="gpt-5.1", tools=None, system_prompt=None, name="my_agent"):
        from langchain.agents import create_agent

        client = chat_openai_client.with_config(model=model, timeout=30)

        return create_agent(model=client, tools=tools, system_prompt=system_prompt, name=name)

    return _create_agent


@reset_core_stats_engine()
@validate_custom_event_count(count=CLIENT_EVENT_COUNT)
@background_task()
def test_state_graph_with_client_invoke(chat_openai_client, exercise_graph):
    def state_graph_invoke(state):
        response = chat_openai_client.invoke(state["messages"])
        return {"messages": [response]}

    response = exercise_graph(_build_graph(state_graph_invoke), CLIENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_event_count(count=CLIENT_EVENT_COUNT)
@background_task()
def test_state_graph_with_client_ainvoke(chat_openai_client, exercise_graph):
    async def state_graph_ainvoke(state):
        response = await chat_openai_client.ainvoke(state["messages"])
        return {"messages": [response]}

    response = exercise_graph(_build_graph(state_graph_ainvoke), CLIENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_event_count(count=CLIENT_EVENT_COUNT)
@background_task()
def test_state_graph_with_client_stream(chat_openai_client, exercise_graph):
    def state_graph_stream(state):
        chunks = list(chat_openai_client.stream(state["messages"]))
        return {"messages": ["".join(chunk.content for chunk in chunks)]}

    response = exercise_graph(_build_graph(state_graph_stream), CLIENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_event_count(count=CLIENT_EVENT_COUNT)
@background_task()
def test_state_graph_with_client_astream(chat_openai_client, exercise_graph):
    async def state_graph_astream(state):
        chunks = [chunk async for chunk in chat_openai_client.astream(state["messages"])]
        return {"messages": ["".join(chunk.content for chunk in chunks)]}

    response = exercise_graph(_build_graph(state_graph_astream), CLIENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(agent_recorded_events)
@validate_custom_event_count(count=AGENT_EVENT_COUNT)
@background_task()
def test_state_graph_with_agent_invoke(exercise_graph, create_agent):
    my_agent = create_agent(tools=[add_exclamation], system_prompt="You are a text manipulation algorithm.")

    def state_graph_invoke(state):
        response = my_agent.invoke({"messages": state["messages"]})
        return {"messages": response.get("messages", [])}

    response = exercise_graph(_build_graph(state_graph_invoke), AGENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(agent_recorded_events)
@validate_custom_event_count(count=AGENT_EVENT_COUNT)
@background_task()
def test_state_graph_with_agent_ainvoke(exercise_graph, create_agent):
    my_agent = create_agent(tools=[add_exclamation], system_prompt="You are a text manipulation algorithm.")

    async def state_graph_ainvoke(state):
        response = await my_agent.ainvoke({"messages": state["messages"]})
        return {"messages": response.get("messages", [])}

    response = exercise_graph(_build_graph(state_graph_ainvoke), AGENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(agent_recorded_events)
@validate_custom_event_count(count=AGENT_EVENT_COUNT)
@background_task()
def test_state_graph_with_agent_stream(exercise_graph, create_agent):
    my_agent = create_agent(tools=[add_exclamation], system_prompt="You are a text manipulation algorithm.")

    def state_graph_stream(state):
        chunks = list(my_agent.stream({"messages": state["messages"]}))
        messages = []
        for event in chunks:
            if not isinstance(event, dict):
                continue
            for value in event.values():
                if isinstance(value, dict):
                    messages.extend(value.get("messages", []))
        return {"messages": messages}

    response = exercise_graph(_build_graph(state_graph_stream), AGENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(agent_recorded_events)
@validate_custom_event_count(count=AGENT_EVENT_COUNT)
@background_task()
def test_state_graph_with_agent_astream(exercise_graph, create_agent):
    my_agent = create_agent(tools=[add_exclamation], system_prompt="You are a text manipulation algorithm.")

    async def state_graph_astream(state):
        chunks = [chunk async for chunk in my_agent.astream({"messages": state["messages"]})]
        messages = []
        for event in chunks:
            if not isinstance(event, dict):
                continue
            for value in event.values():
                if isinstance(value, dict):
                    messages.extend(value.get("messages", []))
        return {"messages": messages}

    response = exercise_graph(_build_graph(state_graph_astream), AGENT_PROMPT)
    assert response


@pytest.fixture
def exercise_graph(loop, exercise_method, exercise_method_version):
    # Shorthand variable names
    method = exercise_method
    version = exercise_method_version

    # Omit the kwarg entirely when version is None so the library default runs.
    version_kwargs = {} if version is None else {"version": version}

    def _exercise_graph(graph, prompt):
        try:
            if method == "invoke":
                return graph.invoke(prompt, **version_kwargs)
            elif method == "ainvoke":
                return loop.run_until_complete(graph.ainvoke(prompt, **version_kwargs))
            elif method == "stream":
                return list(graph.stream(prompt, **version_kwargs))
            elif method == "astream":

                async def _collect_astream():
                    return [event async for event in graph.astream(prompt, **version_kwargs)]

                return loop.run_until_complete(_collect_astream())
            elif method == "astream_events":
                if version == "v3":
                    # v3 returns an awaitable resolving to a typed stream.
                    # Drive it with .output(), and return the final state.
                    async def _collect_astream_events_v3():
                        run = await graph.astream_events(prompt, version="v3")
                        return await run.output()

                    return loop.run_until_complete(_collect_astream_events_v3())
                else:

                    async def _collect_astream_events_v1_v2():
                        return [event async for event in graph.astream_events(prompt, **version_kwargs)]

                    return loop.run_until_complete(_collect_astream_events_v1_v2())
            elif method == "stream_events":
                if version == "v3":
                    # v3 returns an awaitable resolving to a typed stream.
                    # Drive it with .output(), and return the final state.
                    return graph.stream_events(prompt, version="v3").output

                else:
                    raise RuntimeError("Unexpected Combination")
            else:
                raise RuntimeError("Unexpected Combination")
        except TypeError as exc:
            # Async nodes cannot be run via langgraph's sync APIs (invoke/stream/stream_events).
            if "No synchronous function provided" in str(exc):
                pytest.skip(f"Cannot invoke an async node via a synchronous api. (Tried {method})")
            raise

    return _exercise_graph
