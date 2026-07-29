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
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.hooks.mlmodel_langchain import _is_local_tool

PROMPT = {
    "messages": [
        HumanMessage(
            'Call the add_exclamation_mcp tool with message="Hello". Reply with only the tool output, no other text.'
        )
    ]
}

tool_recorded_event = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": None,
            # MCP adapters return the result as a content block carrying a random uuid, so
            # the exact output string is non-deterministic. We can only assert the key
            # is present, not its value.
            "output": None,
            "name": "add_exclamation_mcp",
            "agent_name": "my_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'message': 'Hello'}",
            "vendor": "langchain",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]


@pytest.fixture
def mcp_server():
    server = FastMCP("Test Tools")

    @server.tool()
    def add_exclamation_mcp(message: str) -> str:
        """Adds an exclamation mark to the input message."""
        return f"{message}!"

    return server


@dt_enabled
@reset_core_stats_engine()
def test_remote_mcp_tool_no_subcomponent(loop, set_trace_info, chat_openai_client, mcp_server):
    @validate_custom_events(tool_recorded_event)
    @validate_transaction_metrics(
        "test_remote_mcp_tool_no_subcomponent",
        scoped_metrics=[("Llm/tool/LangChain/arun/add_exclamation_mcp", 1)],
        rollup_metrics=[("Llm/tool/LangChain/arun/add_exclamation_mcp", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    # Agent span still has a subcomponent attribute as the agent is executing locally
    @validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
    # Tool span must NOT have a subcomponent attribute as it will be captured on the server side
    @validate_span_events(
        count=1,
        exact_intrinsics={"name": "Llm/tool/LangChain/arun/add_exclamation_mcp"},
        unexpected_agents=["subcomponent"],
    )
    @background_task(name="test_remote_mcp_tool_no_subcomponent")
    def _test():
        set_trace_info()

        async def _run():
            from langchain.agents import create_agent
            from langchain_mcp_adapters.tools import load_mcp_tools

            async with create_connected_server_and_client_session(mcp_server) as session:
                tools = await load_mcp_tools(session)
                # The loaded tool is a genuine remote proxy, so the fix must treat it as non-local.
                assert _is_local_tool(tools[0]) is False

                agent = create_agent(
                    model=chat_openai_client.with_config(model="gpt-5.1", timeout=30),
                    tools=tools,
                    system_prompt="You are a text manipulation algorithm.",
                    name="my_agent",
                )
                return await agent.ainvoke(PROMPT)

        loop.run_until_complete(_run())

    _test()
