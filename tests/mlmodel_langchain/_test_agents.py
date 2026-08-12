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

import pytest
from langchain_core.messages.tool import ToolMessage

from .conftest import EXPECTED_AGENT_RESPONSE, EXPECTED_TOOL_OUTPUT


def state_function_step(state):
    return {"messages": [f"The real agent said: {state['messages'][-1].content}"]}


def append_function_step(state):
    # Unpack the messages block from however deep it is nested
    if "data" in state:
        messages = state["data"]["model"]["messages"]
    elif "messages" in state:
        messages = state["messages"]
    else:
        messages = state["model"]["messages"]

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
        raise RuntimeError("Unexpected Combination")


@pytest.fixture
def validate_agent_output(agent_runnable_type):
    def _node_payload(event):
        # v2 stream/astream yields StreamPart typed dicts that wrap the {node: output} update
        # map under a "data" key. v1 yields that map directly.
        payload = event["data"] if isinstance(event, dict) and "type" in event and "data" in event else event
        # UpdatesStreamPart.data may also carry __metadata__/__interrupt__ keys, skip them.
        return next(value for key, value in payload.items() if not key.startswith("__"))

    def _content(message):
        # v3 carries message content as a list of typed content blocks
        # (e.g. [{"type": "text", "text": "Hello!"}]) rather than a plain string; flatten
        # it back to text so the shared assertions work across all versions.
        content = message.content
        if isinstance(content, list):
            return "".join(block.get("text", "") for block in content if isinstance(block, dict))
        return content

    def _unpack_messages(response):
        if isinstance(response, list) and not any(response):
            # Only None are returned from RunnableSeq.stream(), avoid the crash
            return []
        elif isinstance(response, list):
            # stream returns a list of events. Messages are packaged into nested dicts with a
            # "model" or "tool_call" key, a "messages" key, which contains a list with one or
            # more messages in order. To unpack everything, we extract each event's node
            # payload (unwrapping v2 StreamParts) and flatten the messages lists.
            messages_packed = [_node_payload(event)["messages"] for event in response]

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
                assert _content(messages[1]) == EXPECTED_TOOL_OUTPUT
                assert _content(messages[2]) == EXPECTED_AGENT_RESPONSE
            else:
                # Events: input prompt, agent calling tool, tool return value, agent output
                assert len(messages) == 4
                assert messages[1].tool_calls
                assert _content(messages[2]) == EXPECTED_TOOL_OUTPUT
                assert _content(messages[3]) == EXPECTED_AGENT_RESPONSE

        elif agent_runnable_type == "StateGraph":
            # Events: input prompt, agent calling tool, tool return value, agent output, function_step output
            assert len(messages) == 5
            assert messages[1].tool_calls
            assert _content(messages[2]) == EXPECTED_TOOL_OUTPUT
            assert _content(messages[3]) == EXPECTED_AGENT_RESPONSE

        elif agent_runnable_type == "RunnableSeq":
            # stream and astream do not directly output anything for RunnableSeq, and can't be validated.
            if not is_streaming:
                # Events: input prompt, agent calling tool, tool return value, agent output, function_step output
                assert len(messages) == 5
                assert messages[1].tool_calls
                assert _content(messages[2]) == EXPECTED_TOOL_OUTPUT
                assert _content(messages[3]) == EXPECTED_AGENT_RESPONSE

        elif agent_runnable_type == "RunnableSequence":
            if is_streaming:
                # Events: agent output, function_step output
                assert len(messages) == 2
                assert _content(messages[0]) == EXPECTED_AGENT_RESPONSE
            else:
                # Events: input prompt, agent calling tool, tool return value, agent output, function_step output
                assert len(messages) == 5
                assert messages[1].tool_calls
                assert _content(messages[2]) == EXPECTED_TOOL_OUTPUT
                assert _content(messages[3]) == EXPECTED_AGENT_RESPONSE

        else:
            raise RuntimeError("Unexpected Combination")

    return _validate_agent_output


# Each exercise method is tested only across the LangChain "version" values it actually
# accepts as an argument. (None pass no argument and uses the default value). Version
# support still varies by runnable type, run-method versions and the v3 protocol require
# a langgraph Pregel graph so the exercise_agent fixture skips the runnable-type combinations
# that can't run. This list is shared with test_state_graph.py's exercise_graph fixture via import.
EXERCISE_PARAMS = [
    # Run methods take version arg only on langgraph Pregel graphs. Other runnables do not take a version arg.
    pytest.param(("invoke", None), id="invoke-default"),
    pytest.param(("invoke", "v1"), id="invoke-v1"),
    pytest.param(("invoke", "v2"), id="invoke-v2"),
    pytest.param(("ainvoke", None), id="ainvoke-default"),
    pytest.param(("ainvoke", "v1"), id="ainvoke-v1"),
    pytest.param(("ainvoke", "v2"), id="ainvoke-v2"),
    pytest.param(("stream", None), id="stream-default"),
    pytest.param(("stream", "v1"), id="stream-v1"),
    pytest.param(("stream", "v2"), id="stream-v2"),
    pytest.param(("astream", None), id="astream-default"),
    pytest.param(("astream", "v1"), id="astream-v1"),
    pytest.param(("astream", "v2"), id="astream-v2"),
    # astream_events v3 only executes on a Pregel graph.
    pytest.param(("astream_events", None), id="astream_events-default"),
    pytest.param(("astream_events", "v1"), id="astream_events-v1"),
    pytest.param(("astream_events", "v2"), id="astream_events-v2"),
    # TODO: Add testing for v3 API versions
]


@pytest.fixture(params=EXERCISE_PARAMS)
def exercise_method_params(request):
    """Helper fixture that parametrizes exercise_agent and exercise_graph."""
    return request.param


@pytest.fixture
def exercise_method(exercise_method_params):
    return exercise_method_params[0]


@pytest.fixture
def exercise_method_version(exercise_method_params):
    return exercise_method_params[1]


@pytest.fixture
def exercise_agent(loop, validate_agent_output, agent_runnable_type, exercise_method, exercise_method_version):
    # Shorthand variable names
    method = exercise_method
    version = exercise_method_version

    # Omit the kwarg entirely when version is None so the library default runs.
    version_kwargs = {} if version is None else {"version": version}

    def _exercise_agent(agent, prompt):
        try:
            if method == "invoke":
                response = agent.invoke(prompt, **version_kwargs)
                validate_agent_output(response)
                return response
            elif method == "ainvoke":
                response = loop.run_until_complete(agent.ainvoke(prompt, **version_kwargs))
                validate_agent_output(response)
                return response
            elif method == "stream":
                response = list(agent.stream(prompt, **version_kwargs))
                validate_agent_output(response)
                return response
            elif method == "astream":

                async def _collect_astream():
                    return [event async for event in agent.astream(prompt, **version_kwargs)]

                response = loop.run_until_complete(_collect_astream())
                validate_agent_output(response)
                return response
            elif method == "astream_events":
                if version == "v3":
                    # v3 returns an awaitable resolving to a typed stream.
                    # Drive it with .output(), and return the final state.
                    async def _collect_astream_events_v3():
                        run = await agent.astream_events(prompt, version="v3")
                        return await run.output()

                    response = loop.run_until_complete(_collect_astream_events_v3())
                    validate_agent_output(response)
                    return response
                else:

                    async def _collect_astream_events_v1_v2():
                        return [event async for event in agent.astream_events(prompt, **version_kwargs)]

                    events = loop.run_until_complete(_collect_astream_events_v1_v2())
                    root_run_id = events[0]["run_id"] if events else None
                    response = [
                        event["data"]["chunk"]
                        for event in events
                        if event["event"] == "on_chain_stream" and event["run_id"] == root_run_id
                    ]
                    validate_agent_output(response)
                    return response
            elif method == "stream_events":
                if version == "v3":
                    # v3 returns an awaitable resolving to a typed stream.
                    # Drive it with .output(), and return the final state.
                    response = agent.stream_events(prompt, version="v3").output
                    validate_agent_output(response)
                    return response
                else:
                    raise RuntimeError("Unexpected Combination")
            else:
                raise RuntimeError("Unexpected Combination")
        except NotImplementedError:
            # Catch any not implemented combinations of Runnable and method version.
            # If we were expecting this combination not to work, issue a pytest.skip
            # with an appropriate message.
            raise

    # Expected number of events for a full run of the agent
    if agent_runnable_type != "RunnableSequence":
        _exercise_agent._expected_event_count = 11
        _exercise_agent._expected_event_count_error = 5
    elif method in {"invoke", "ainvoke"}:
        _exercise_agent._expected_event_count = 14
        _exercise_agent._expected_event_count_error = 7
    else:
        _exercise_agent._expected_event_count = 13
        _exercise_agent._expected_event_count_error = 7

    return _exercise_agent


@pytest.fixture
def agent_method_metric(agent_runnable_type, exercise_method, exercise_method_version):
    # Shorthand variable names
    method = exercise_method
    version = exercise_method_version

    def _invoked_method_name():
        """
        The actual method name driven under the hood determines how we name the agent metric.
        This may not necessarily match the method called on the Runnable. All known cases are documented here.
        """
        if method in {"astream_events", "stream_events"}:
            # (a)stream_events on any Runnable other than directly calling on the agent will run through a different
            # function under the hood.
            if agent_runnable_type == "create_agent":
                # Directly calling (a)stream_events on the agent produces the same metric name
                return method
            elif agent_runnable_type == "StateGraph" and version == "v3":
                # The v3 protocol drives the nested node via (a)invoke rather than streaming it.
                return "invoke" if method == "stream_events" else "ainvoke"
            else:
                # All other Runnables will call (a)stream instead of (a)stream_events
                return "astream" if method == "astream_events" else "stream"

        if agent_runnable_type == "StateGraph":
            # StateGraph will only call "invoke" or "ainvoke", even when streaming
            if method in {"invoke", "stream"}:
                return "invoke"
            else:
                return "ainvoke"

        return method

    method_name = _invoked_method_name()
    return (f"Llm/agent/LangChain/{method_name}/my_agent", 1)
