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
import json
import os
from pathlib import Path

import pytest
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
)
from testing_support.ml_testing_utils import set_trace_info

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper
from newrelic.common.signature import bind_args

from ._mock_external_openai_server import MockExternalOpenAIServer, extract_shortened_prompt, simple_get

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


OPENAI_AUDIT_LOG_FILE = Path(__file__).parent / "openai_audit.log"
OPENAI_AUDIT_LOG_CONTENTS = {}
# Intercept outgoing requests and log to file for mocking
RECORDED_HEADERS = {"x-request-id", "content-type"}
EXPECTED_AGENT_RESPONSE = 'The word "Hello" with an exclamation mark added is "Hello!"'
EXPECTED_TOOL_OUTPUT = "Hello!"


@pytest.fixture(scope="session")
def openai_clients(MockExternalOpenAIServer):
    """
    This configures the openai client and returns it for openai v1 and only configures
    openai for v0 since there is no client.
    """
    from newrelic.core.config import _environ_as_bool

    if not _environ_as_bool("NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES", False):
        with MockExternalOpenAIServer() as server:
            chat = ChatOpenAI(base_url=f"http://localhost:{server.port}", api_key="NOT-A-REAL-SECRET", temperature=0.7)
            embeddings = OpenAIEmbeddings(
                openai_api_key="NOT-A-REAL-SECRET", openai_api_base=f"http://localhost:{server.port}"
            )
            yield chat, embeddings
    else:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required.")
        chat = ChatOpenAI(api_key=openai_api_key)
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        yield chat, embeddings


@pytest.fixture(scope="session")
def embedding_openai_client(openai_clients):
    _, embedding_client = openai_clients
    return embedding_client


@pytest.fixture(scope="session")
def chat_openai_client(openai_clients):
    chat_client, _ = openai_clients
    return chat_client


def state_function_step(state):
    return {"messages": [f"The real agent said: {state['messages'][-1].content}"]}


def append_function_step(state):
    from langchain.messages import ToolMessage

    messages = state["messages"] if "messages" in state else state["model"]["messages"]
    messages.append(ToolMessage(f"The real agent said: {messages[-1].content}", tool_call_id=123))
    return state


@pytest.fixture(scope="session", params=["create_agent"])
# @pytest.fixture(scope="session", params=["create_agent", "StateGraph", "RunnableSeq", "RunnableSequence"])
def agent_runnable_type(request):
    return request.param


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
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
            messages_packed = [next(iter(event.values()))["messages"] for event in response]
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


@pytest.fixture(scope="session", params=["invoke", "ainvoke", "stream", "astream"])
def exercise_agent(request, loop, validate_agent_output):
    def _exercise_agent(agent, prompt):
        if request.param == "invoke":
            response = agent.invoke(prompt)
            validate_agent_output(response)
            return response
        elif request.param == "ainvoke":
            response = loop.run_until_complete(agent.ainvoke(prompt))
            validate_agent_output(response)
            return response
        elif request.param == "stream":
            response = list(agent.stream(prompt))
            validate_agent_output(response)
            return response
        elif request.param == "astream":

            async def _exercise_agen():
                return [event async for event in agent.astream(prompt)]

            response = loop.run_until_complete(_exercise_agen())
            validate_agent_output(response)
            return response
        else:
            raise NotImplementedError

    return _exercise_agent


@pytest.fixture(autouse=True, scope="session")
def openai_server(wrap_httpx_client_send, wrap_stream_iter_events):
    """
    This fixture will either create a mocked backend for testing purposes, or will
    set up an audit log file to log responses of the real OpenAI backend to a file.
    The behavior can be controlled by setting NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES=1 as
    an environment variable to run using the real OpenAI backend. (Default: mocking)
    """
    from newrelic.core.config import _environ_as_bool

    if _environ_as_bool("NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES", False):
        wrap_function_wrapper("httpx._client", "Client.send", wrap_httpx_client_send)
        wrap_function_wrapper("openai._streaming", "Stream._iter_events", wrap_stream_iter_events)
        yield  # Run tests
        # Write responses to audit log
        with OPENAI_AUDIT_LOG_FILE.open("w") as audit_log_fp:
            json.dump(OPENAI_AUDIT_LOG_CONTENTS, fp=audit_log_fp, indent=4)
    else:
        # We are mocking openai responses so we don't need to do anything in this case.
        yield


@pytest.fixture(scope="session")
def wrap_httpx_client_send():
    def _wrap_httpx_client_send(wrapped, instance, args, kwargs):
        bound_args = bind_args(wrapped, args, kwargs)
        stream = bound_args.get("stream", False)
        request = bound_args["request"]

        if not request:
            return wrapped(*args, **kwargs)

        params = json.loads(request.content.decode("utf-8"))
        prompt = extract_shortened_prompt(params)

        # Send request
        response = wrapped(*args, **kwargs)

        if response.status_code >= 400 or response.status_code < 200:
            prompt = "error"

        rheaders = response.headers

        headers = dict(
            filter(
                lambda k: k[0].lower() in RECORDED_HEADERS
                or k[0].lower().startswith("openai")
                or k[0].lower().startswith("x-ratelimit"),
                rheaders.items(),
            )
        )

        # Append response data to log
        if stream:
            OPENAI_AUDIT_LOG_CONTENTS[prompt] = [headers, response.status_code, []]
            if prompt == "error":
                OPENAI_AUDIT_LOG_CONTENTS[prompt][2] = json.loads(response.read())
        else:
            body = json.loads(response.content.decode("utf-8"))
            OPENAI_AUDIT_LOG_CONTENTS[prompt] = headers, response.status_code, body
        return response

    return _wrap_httpx_client_send


@pytest.fixture(scope="session")
def generator_proxy():
    class GeneratorProxy(ObjectProxy):
        def __init__(self, wrapped):
            super().__init__(wrapped)

        def __iter__(self):
            return self

        # Make this Proxy a pass through to our instrumentation's proxy by passing along
        # get attr and set attr calls to our instrumentation's proxy.
        def __getattr__(self, attr):
            return self.__wrapped__.__getattr__(attr)

        def __setattr__(self, attr, value):
            return self.__wrapped__.__setattr__(attr, value)

        def __next__(self):
            transaction = current_transaction()
            if not transaction:
                return self.__wrapped__.__next__()

            try:
                return_val = self.__wrapped__.__next__()
                if return_val:
                    prompt = list(OPENAI_AUDIT_LOG_CONTENTS.keys())[-1]
                    if not getattr(return_val, "data", "").startswith("[DONE]"):
                        OPENAI_AUDIT_LOG_CONTENTS[prompt][2].append(return_val.json())
                return return_val
            except Exception:
                raise

        def close(self):
            return super().close()

    return GeneratorProxy


@pytest.fixture(scope="session")
def wrap_stream_iter_events(generator_proxy):
    def _wrap_stream_iter_events(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if not transaction:
            return wrapped(*args, **kwargs)

        return_val = wrapped(*args, **kwargs)
        proxied_return_val = generator_proxy(return_val)
        return proxied_return_val

    return _wrap_stream_iter_events
