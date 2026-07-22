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

from typing import Annotated, TypedDict
import os
import pytest

from newrelic.api.transaction import current_transaction
from testing_support.fixture.event_loop import event_loop as loop

from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient


# Initialize MCP Client and load tools
@pytest.fixture(scope="session")
def mcp_client():
    mcp_client = MultiServerMCPClient(
        {
            "my_mcp_server": {
                "command": "python",
                "args": ["tests/mlmodel_gemini/langchain_integration/_mcp_server.py"],
                "transport": "stdio",
            }
        }
    )
    
    yield mcp_client


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

    yield init_chat_model(
        "gemini-3.5-flash",
        model_provider="google_genai",
        streaming=True,
    )


# Build graph
@pytest.fixture
def build_agent(loop, mcp_client, schemas, gemini_streaming_client):
    def _create_agent():
        from langchain.agents import create_agent
        from langchain.agents.structured_output import ToolStrategy

        agent_tools = loop.run_until_complete(mcp_client.get_tools())
        Schema, State = schemas

        return create_agent(
            model=gemini_streaming_client,
            name="my_agent",
            tools=agent_tools,
            state_schema=State,
            response_format=ToolStrategy(Schema),
        )

    return _create_agent


@pytest.fixture
def async_build_state_graph(async_call_model, async_extra_node, schemas):
    def _graph(agent):
        from langgraph.graph import StateGraph, START, END

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
        return "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        )
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

            step = 0
            async for event in agent.astream({"messages": state["messages"]}, stream_mode="updates"):
                for _, update in event.items():
                    if isinstance(update, dict) and update.get("messages"):
                        for message in update["messages"]:
                            try:
                                # AIMessage
                                original_tool_id = message.tool_calls[-1]["id"]
                                message.tool_calls[-1]["id"] = f"tool-id-{step}"
                                thought_signature = message.additional_kwargs["__gemini_function_call_thought_signatures__"].pop(original_tool_id)
                                message.additional_kwargs["__gemini_function_call_thought_signatures__"] = {f"tool-id-{step}": thought_signature}
                                message.id = f"lc_run--ai-message-id-{step}"
                            except AttributeError:
                                # ToolMessage
                                if isinstance(message.content, list):
                                    message.content[-1]["id"] = f"lc_tool-message-content-id-{step}"
                                else:
                                    message.tool_call_id = f"tool-id-{step}"
                                message.id = f"tool-message-id-{step}"
                        yield {"messages": update["messages"]}
                step += 1

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
