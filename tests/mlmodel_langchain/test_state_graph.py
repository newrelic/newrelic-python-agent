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
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_custom_events import validate_custom_events

from newrelic.api.background_task import background_task

PROMPT = {"messages": [HumanMessage('Use a tool to add an exclamation to the word "Hello"')]}

chat_completion_recorded_events = [
    [
        {"type": "LlmChatCompletionSummary"},
        {
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request_id": "req_22204b237d22427fbfd99c665d8a9964",
            "response.choices.finish_reason": "stop",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 10000,
            "response.headers.ratelimitLimitTokens": 50000000,
            "response.headers.ratelimitRemainingRequests": 9999,
            "response.headers.ratelimitRemainingTokens": 49999985,
            "response.headers.ratelimitResetRequests": "6ms",
            "response.headers.ratelimitResetTokens": "0s",
            "response.model": "gpt-3.5-turbo-0125",
            "response.number_of_messages": 2,
            "response.organization": "nr-test-org",
            "response.usage.completion_tokens": 2,
            "response.usage.prompt_tokens": 21,
            "response.usage.total_tokens": 23,
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
            "content": 'Use a tool to add an exclamation to the word "Hello"',
            "id": "chatcmpl-Dd0Na8gXEDyFIhYMsL72TYk3bSZun-0",
            "ingest_source": "Python",
            "request_id": "req_22204b237d22427fbfd99c665d8a9964",
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
            "content": "Hello!",
            "id": "chatcmpl-Dd0Na8gXEDyFIhYMsL72TYk3bSZun-1",
            "ingest_source": "Python",
            "is_response": True,
            "request_id": "req_22204b237d22427fbfd99c665d8a9964",
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

chat_completion_stream_recorded_events = [
    [
        {"type": "LlmChatCompletionSummary"},
        {
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request_id": "req_4566af5dd7224f00a2407fa1d3e32864",
            "response.choices.finish_reason": "stop",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 10000,
            "response.headers.ratelimitLimitTokens": 50000000,
            "response.headers.ratelimitRemainingRequests": 9999,
            "response.headers.ratelimitRemainingTokens": 49999985,
            "response.headers.ratelimitResetRequests": "6ms",
            "response.headers.ratelimitResetTokens": "0s",
            "response.model": "gpt-3.5-turbo-0125",
            "response.number_of_messages": 2,
            "response.organization": "nr-test-org",
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
            "content": 'Use a tool to add an exclamation to the word "Hello"',
            "id": "chatcmpl-DelITaJCJy951hwON0psdz2H9dF7i-0",
            "ingest_source": "Python",
            "request_id": "req_4566af5dd7224f00a2407fa1d3e32864",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "user",
            "sequence": 0,
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
            "content": "Hello!",
            "id": "chatcmpl-DelITaJCJy951hwON0psdz2H9dF7i-1",
            "ingest_source": "Python",
            "is_response": True,
            "request_id": "req_4566af5dd7224f00a2407fa1d3e32864",
            "response.model": "gpt-3.5-turbo-0125",
            "role": "assistant",
            "sequence": 1,
            "span_id": None,
            "trace_id": None,
            "vendor": "openai",
        },
    ],
]


def _build_graph(node):
    from langgraph.graph import END, START, MessagesState, StateGraph

    builder = StateGraph(MessagesState)
    builder.add_node("my_agent", node)
    builder.add_edge(START, "my_agent")
    builder.add_edge("my_agent", END)
    return builder.compile()


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
@background_task()
def test_state_graph_with_client_invoke(chat_openai_client, exercise_graph):
    def state_graph_invoke(state):
        response = chat_openai_client.invoke(state["messages"])
        return {"messages": [response]}

    response = exercise_graph(_build_graph(state_graph_invoke), PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
@background_task()
def test_state_graph_with_client_ainvoke(chat_openai_client, exercise_graph):
    async def state_graph_ainvoke(state):
        response = await chat_openai_client.ainvoke(state["messages"])
        return {"messages": [response]}

    response = exercise_graph(_build_graph(state_graph_ainvoke), PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(chat_completion_stream_recorded_events)
@background_task()
def test_state_graph_with_client_stream(chat_openai_client, exercise_graph):
    def state_graph_stream(state):
        chunks = list(chat_openai_client.stream(state["messages"]))
        return {"messages": ["".join(chunk.content for chunk in chunks)]}

    response = exercise_graph(_build_graph(state_graph_stream), PROMPT)
    assert response


@reset_core_stats_engine()
@validate_custom_events(chat_completion_stream_recorded_events)
@background_task()
def test_state_graph_with_client_astream(chat_openai_client, exercise_graph):
    async def state_graph_astream(state):
        chunks = [chunk async for chunk in chat_openai_client.astream(state["messages"])]
        return {"messages": ["".join(chunk.content for chunk in chunks)]}

    response = exercise_graph(_build_graph(state_graph_astream), PROMPT)
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
