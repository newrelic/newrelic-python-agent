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
from testing_support.validators.validate_custom_events import validate_custom_events

from newrelic.api.background_task import background_task

CLIENT_PROMPT = {"messages": [HumanMessage("What is the capital of France? Answer in one word.")]}
AGENT_PROMPT = {
    "messages": [
        HumanMessage(
            'Call the add_exclamation tool with message="Hello". Reply with only the tool output, no other text.'
        )
    ]
}

client_recorded_events = [
    [
        {"type": "LlmChatCompletionSummary"},
        {
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request_id": "req_ac60b6a469084412a5496bc5c71d8801",
            "response.choices.finish_reason": "stop",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 10000,
            "response.headers.ratelimitLimitTokens": 50000000,
            "response.headers.ratelimitRemainingRequests": 9999,
            "response.headers.ratelimitRemainingTokens": 49999975,
            "response.headers.ratelimitResetRequests": "6ms",
            "response.headers.ratelimitResetTokens": "0s",
            "response.model": "gpt-3.5-turbo-0125",
            "response.number_of_messages": 2,
            "response.organization": "nr-test-org",
            "response.usage.completion_tokens": 1,
            "response.usage.prompt_tokens": 19,
            "response.usage.total_tokens": 20,
            "span_id": None,
            "timestamp": None,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": "What is the capital of France? Answer in one word.",
            "id": "chatcmpl-DyjxXP7QeqZsp81qtbX65us41OVKg-0",
            "ingest_source": "Python",
            "request_id": "req_ac60b6a469084412a5496bc5c71d8801",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "user",
            "sequence": 0,
            "span_id": None,
            "timestamp": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": "Paris",
            "id": "chatcmpl-DyjxXP7QeqZsp81qtbX65us41OVKg-1",
            "ingest_source": "Python",
            "is_response": True,
            "request_id": "req_ac60b6a469084412a5496bc5c71d8801",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "assistant",
            "sequence": 1,
            "span_id": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
]

client_stream_recorded_events = [
    [
        {"type": "LlmChatCompletionSummary"},
        {
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request_id": "req_ac60b6a469084412a5496bc5c71d8801",
            "response.choices.finish_reason": "stop",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 10000,
            "response.headers.ratelimitLimitTokens": 50000000,
            "response.headers.ratelimitRemainingRequests": 9999,
            "response.headers.ratelimitRemainingTokens": 49999975,
            "response.headers.ratelimitResetRequests": "6ms",
            "response.headers.ratelimitResetTokens": "0s",
            "response.model": "gpt-3.5-turbo-0125",
            "response.number_of_messages": 2,
            "response.organization": "nr-test-org",
            # langchain's ChatOpenAI.stream() passes stream_options={"include_usage": True}
            # by default, so the final usage chunk is captured and these are populated.
            "response.usage.completion_tokens": 1,
            "response.usage.prompt_tokens": 19,
            "response.usage.total_tokens": 20,
            "span_id": None,
            "time_to_first_token": None,
            "timestamp": None,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": "What is the capital of France? Answer in one word.",
            "id": "chatcmpl-DyjxXP7QeqZsp81qtbX65us41OVKg-0",
            "ingest_source": "Python",
            "request_id": "req_ac60b6a469084412a5496bc5c71d8801",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "user",
            "sequence": 0,
            "span_id": None,
            "timestamp": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": "Paris",
            "id": "chatcmpl-DyjxXP7QeqZsp81qtbX65us41OVKg-1",
            "ingest_source": "Python",
            "is_response": True,
            "request_id": "req_ac60b6a469084412a5496bc5c71d8801",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "assistant",
            "sequence": 1,
            "span_id": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
]


agent_recorded_events = [
    [
        {"timestamp": None, "type": "LlmChatCompletionSummary"},
        {
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request_id": "req_d20f8e8fdc394022a8b95f62ace42b10",
            "response.choices.finish_reason": "tool_calls",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 10000,
            "response.headers.ratelimitLimitTokens": 50000000,
            "response.headers.ratelimitRemainingRequests": 9999,
            "response.headers.ratelimitRemainingTokens": 49999975,
            "response.headers.ratelimitResetRequests": "6ms",
            "response.headers.ratelimitResetTokens": "0s",
            "response.model": "gpt-3.5-turbo-0125",
            "response.number_of_messages": 2,
            "response.organization": "nr-test-org",
            "response.usage.completion_tokens": 15,
            "response.usage.prompt_tokens": 78,
            "response.usage.total_tokens": 93,
            "span_id": None,
            "timestamp": None,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"timestamp": None, "type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": "You are a text manipulation algorithm.",
            "id": "chatcmpl-DyjwBisOslzESdW8A2OhHO1xk3qPK-0",
            "ingest_source": "Python",
            "request_id": "req_d20f8e8fdc394022a8b95f62ace42b10",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "system",
            "sequence": 0,
            "span_id": None,
            "timestamp": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"timestamp": None, "type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": 'Call the add_exclamation tool with message="Hello". Reply with only the tool output, no other text.',
            "id": "chatcmpl-DyjwBisOslzESdW8A2OhHO1xk3qPK-1",
            "ingest_source": "Python",
            "request_id": "req_d20f8e8fdc394022a8b95f62ace42b10",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "user",
            "sequence": 1,
            "span_id": None,
            "timestamp": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
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
            "run_id": "call_zMq39z2e9dLaMeCsjMSOkys8",
            "span_id": None,
            "trace_id": None,
            "vendor": "langchain",
        },
    ],
    [
        {"timestamp": None, "type": "LlmChatCompletionSummary"},
        {
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request_id": "req_d20f8e8fdc394022a8b95f62ace42b10",
            "response.choices.finish_reason": "stop",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 10000,
            "response.headers.ratelimitLimitTokens": 50000000,
            "response.headers.ratelimitRemainingRequests": 9999,
            "response.headers.ratelimitRemainingTokens": 49999975,
            "response.headers.ratelimitResetRequests": "6ms",
            "response.headers.ratelimitResetTokens": "0s",
            "response.model": "gpt-3.5-turbo-0125",
            "response.number_of_messages": 5,
            "response.organization": "nr-test-org",
            "response.usage.completion_tokens": 2,
            "response.usage.prompt_tokens": 107,
            "response.usage.total_tokens": 109,
            "span_id": None,
            "timestamp": None,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"timestamp": None, "type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": "You are a text manipulation algorithm.",
            "id": "chatcmpl-DyjwCWB6oPS6gcxdy4b9JW4Ey6Lv5-0",
            "ingest_source": "Python",
            "request_id": "req_d20f8e8fdc394022a8b95f62ace42b10",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "system",
            "sequence": 0,
            "span_id": None,
            "timestamp": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"timestamp": None, "type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": 'Call the add_exclamation tool with message="Hello". Reply with only the tool output, no other text.',
            "id": "chatcmpl-DyjwCWB6oPS6gcxdy4b9JW4Ey6Lv5-1",
            "ingest_source": "Python",
            "request_id": "req_d20f8e8fdc394022a8b95f62ace42b10",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "user",
            "sequence": 1,
            "span_id": None,
            "timestamp": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"timestamp": None, "type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "id": "chatcmpl-DyjwCWB6oPS6gcxdy4b9JW4Ey6Lv5-2",
            "ingest_source": "Python",
            "request_id": "req_d20f8e8fdc394022a8b95f62ace42b10",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "assistant",
            "sequence": 2,
            "span_id": None,
            "timestamp": None,
            "trace_id": None,
            "token_count": 0,
            "vendor": "openai",
        },
    ],
    [
        {"timestamp": None, "type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": "Hello!",
            "id": "chatcmpl-DyjwCWB6oPS6gcxdy4b9JW4Ey6Lv5-3",
            "ingest_source": "Python",
            "request_id": "req_d20f8e8fdc394022a8b95f62ace42b10",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "tool",
            "sequence": 3,
            "span_id": None,
            "timestamp": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
    [
        {"timestamp": None, "type": "LlmChatCompletionMessage"},
        {
            "completion_id": None,
            "content": "Hello!",
            "id": "chatcmpl-DyjwCWB6oPS6gcxdy4b9JW4Ey6Lv5-4",
            "ingest_source": "Python",
            "is_response": True,
            "request_id": "req_d20f8e8fdc394022a8b95f62ace42b10",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "assistant",
            "sequence": 4,
            "span_id": None,
            "token_count": 0,
            "trace_id": None,
            "vendor": "openai",
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
@validate_custom_events(client_recorded_events)
@background_task()
def test_state_graph_with_client_invoke(chat_openai_client, exercise_graph):
    def state_graph_invoke(state):
        response = chat_openai_client.invoke(state["messages"])
        return {"messages": [response]}

    response = exercise_graph(_build_graph(state_graph_invoke), CLIENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(client_recorded_events)
@background_task()
def test_state_graph_with_client_ainvoke(chat_openai_client, exercise_graph):
    async def state_graph_ainvoke(state):
        response = await chat_openai_client.ainvoke(state["messages"])
        return {"messages": [response]}

    response = exercise_graph(_build_graph(state_graph_ainvoke), CLIENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(client_stream_recorded_events)
@background_task()
def test_state_graph_with_client_stream(chat_openai_client, exercise_graph):
    def state_graph_stream(state):
        chunks = list(chat_openai_client.stream(state["messages"]))
        return {"messages": ["".join(chunk.content for chunk in chunks)]}

    response = exercise_graph(_build_graph(state_graph_stream), CLIENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(client_stream_recorded_events)
@background_task()
def test_state_graph_with_client_astream(chat_openai_client, exercise_graph):
    async def state_graph_astream(state):
        chunks = [chunk async for chunk in chat_openai_client.astream(state["messages"])]
        return {"messages": ["".join(chunk.content for chunk in chunks)]}

    response = exercise_graph(_build_graph(state_graph_astream), CLIENT_PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(agent_recorded_events)
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


@pytest.fixture(params=["invoke", "ainvoke", "stream", "astream"])
def exercise_graph(request, loop):
    def _exercise_graph(graph, prompt):
        method_called = request.param
        try:
            if method_called == "invoke":
                return graph.invoke(prompt)
            elif method_called == "ainvoke":
                return loop.run_until_complete(graph.ainvoke(prompt))
            elif method_called == "stream":
                return list(graph.stream(prompt))
            elif method_called == "astream":

                async def _exercise_agen():
                    return [event async for event in graph.astream(prompt)]

                return loop.run_until_complete(_exercise_agen())
            else:
                raise NotImplementedError
        except TypeError as exc:
            # Async nodes cannot be run via langgraph's sync APIs (invoke/stream).
            if "No synchronous function provided" in str(exc):
                pytest.skip(f"Cannot invoke an async node via a synchronous api. (Tried {method_called})")
            raise

    return _exercise_graph
