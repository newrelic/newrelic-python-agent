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

import json
import os
import sys
from typing import Annotated

import pytest

if sys.version_info[:2] < (3, 12):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict

from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph.message import add_messages
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixture.vcr import VCR_MATCHERS

from newrelic.api.transaction import current_transaction
from newrelic.common.encoding_utils import ensure_str


def _match_body_no_thought_signature(recorded, current):
    # If original bodies are identical, then it's a match
    if recorded.body == current.body:
        return

    def remove_thought_signature_and_id(body):
        try:
            for content in body["contents"]:
                for part in content["parts"]:
                    part.pop("thoughtSignature", None)
                    if part.get("functionResponse"):
                        for output in part["functionResponse"]["response"]["output"]:
                            output.pop("id", None)
        except Exception:
            pass

    recorded_body = json.loads(ensure_str(recorded.body))
    current_body = json.loads(ensure_str(current.body))

    # If parsed and reserialized JSON is identical, then it's a match
    if json.dumps(recorded_body) == json.dumps(current_body):
        return

    remove_thought_signature_and_id(recorded_body)
    remove_thought_signature_and_id(current_body)

    # If reserialized JSON without thoughtSignature is identical, then it's a match
    assert json.dumps(recorded_body) == json.dumps(current_body)


VCR_MATCHERS["body"] = _match_body_no_thought_signature


@pytest.fixture(autouse=True)
def _force_genai_httpx_transport(monkeypatch):
    """
    Force google-genai onto its httpx async transport for this suite.

    google-genai auto-selects aiohttp whenever aiohttp is importable (it is here, pulled in
    transitively by the langchain dependencies). VCR cannot terminate a replayed aiohttp SSE
    stream, so on replay the aiohttp transport loops forever reading the streamed response and
    exhausts memory. httpx replays streaming responses correctly, so hide aiohttp from
    google-genai (`has_aiohttp` is the first conjunct of `_use_aiohttp()`, so clearing it
    routes streaming requests through the httpx fallback). `monkeypatch` restores it after
    each test; `raising=True` (the default) fails loudly if google-genai renames the flag
    rather than silently regressing to the aiohttp OOM.
    """
    import google.genai._api_client as genai_api_client

    monkeypatch.setattr(genai_api_client, "has_aiohttp", False)


# Initialize MCP Client and load tools
@pytest.fixture(scope="session")
def mcp_client():
    mcp_server_location = "langchain_integration/mcp_server.py" if os.getenv("GITHUB_ACTIONS") else "tests/mlmodel_langchain/gemini_integration/mcp_server.py"

    mcp_client = MultiServerMCPClient(
        {
            "my_mcp_server": {
                "command": sys.executable,
                "args": [mcp_server_location],
                "transport": "stdio",
            }
        }
    )

    return mcp_client


@pytest.fixture
def gemini_streaming_client(vcr_recording):
    """
    This configures the Gemini client to use a fake API key when replaying responses through VCR.

    To record new responses, set a valid API key and run pytest with the flag --record-mode=new_episodes.
    """

    if vcr_recording:
        if not os.environ.get("GOOGLE_API_KEY"):
            raise RuntimeError("GOOGLE_API_KEY environment variable required.")
    else:
        os.environ["GOOGLE_API_KEY"] = "FAKE_GEMINI_API_KEY"

    return init_chat_model("gemini-3.5-flash", model_provider="google_genai", streaming=True)


@pytest.fixture(params=["tool_strategy", "json"])
def response_format(request):
    return request.param


# Build graph
@pytest.fixture
def build_agent(response_format, loop, mcp_client, schemas, gemini_streaming_client):
    def _create_agent():
        from langchain.agents import create_agent
        from langchain.agents.structured_output import ToolStrategy
        from langchain_mcp_adapters.tools import load_mcp_tools

        agent_tools = loop.run_until_complete(mcp_client.get_tools())
        Schema, State = schemas

        kwargs = {"model": gemini_streaming_client, "name": "my_agent", "tools": agent_tools, "state_schema": State}
        
        if response_format == "tool_strategy":
            kwargs.update({"response_format": ToolStrategy(Schema)})

        return create_agent(**kwargs)

    return _create_agent


@pytest.fixture
def async_build_state_graph(async_call_model, async_extra_node, schemas):
    def _graph(agent):
        from langgraph.graph import END, START, StateGraph

        call_model_node = async_call_model(agent)
        extra_graph_node = async_extra_node
        _, State = schemas

        builder = StateGraph(state_schema=State)
        builder.add_node("call_model", call_model_node)
        builder.add_node("extra_node", extra_graph_node)
        builder.add_edge(START, "call_model")
        builder.add_edge("call_model", "extra_node")
        builder.add_edge("extra_node", END)
        graph = builder.compile()

        return graph

    return _graph


def _extract_text(message):
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return ""


@pytest.fixture
def schemas():
    # Define structured data types
    class Schema(TypedDict):
        data: str

    class State(TypedDict):
        messages: Annotated[list, add_messages]
        structured_data: Schema
        structured_response: Schema

    return Schema, State


# Build nodes
@pytest.fixture
def async_call_model():
    def wrapper(agent):
        # Define nodes for StateGraph
        async def _call_model(state):
            # Ensure that context propagation works
            # by checking for a transaction
            assert current_transaction()

            async for event in agent.astream({"messages": state["messages"]}, stream_mode="updates"):
                for update in event.values():
                    if isinstance(update, dict) and update.get("messages"):
                        yield {"messages": update["messages"]}

        return _call_model

    return wrapper


@pytest.fixture
def async_extra_node():
    async def _extra_node(state):
        # Ensure that context propagation works
        # by checking for a transaction
        assert current_transaction()

        return {"messages": [f"The real agent said: {_extract_text(state['messages'][-1])}"]}

    return _extra_node
