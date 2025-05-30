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
from mcp import ClientSession, Tool
from unittest.mock import AsyncMock, patch
from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from newrelic.api.background_task import background_task

@pytest.fixture
def round_robin_group():
    pirate_agent = AssistantAgent(
        name="pirate",
        model_client=model_client,
        tools=tools,  # type: ignore
        system_message=(
            "You are a helpful translation assistant who speaks like a pirate. "
            "You have access to a calculator tool and an agent tool. "
            "You can use the calculator tool to perform calculations. "
            "The agent tool is an expert in python programming and should be used for any programming tasks. "
        ),
        model_client_stream=True,
    )

    robot_agent = AssistantAgent(
        name="robot",
        model_client=model_client,
        tools=tools,  # type: ignore
        system_message=(
            "You are a helpful translation assistant who speaks like a robot. "
            "You have access to a calculator tool and an agent tool. "
            "You can use the calculator tool to perform calculations. "
            "The agent tool is an expert in programming languages other than python and should be used for any programming tasks. "
        ),
        model_client_stream=True,
    )

    agents = RoundRobinGroupChat(
        participants=[orchestrator_agent, pirate_agent, robot_agent],
        max_turns=3
    )

    return robot_agent

# @validate_transaction_metrics(
#     "test_agent_tracing:test_from_server_params_tracing",
#     scoped_metrics=[("Function/autogen_ext.tools.mcp._sse:SseMcpToolAdapter.from_server_params/add_exclamation", 1)],
#     rollup_metrics=[("Function/autogen_ext.tools.mcp._sse:SseMcpToolAdapter.from_server_params/add_exclamation", 1)],
#     background_task=True,
# )
# @background_task()
# def test_from_server_params_tracing(loop):
#     async def _test():
#         server_params = SseServerParams(url="http://test-url", timeout=10)
#
#         # Mock the SseMcpToolAdapter.from_server_params method
#         with patch("autogen_ext.tools.mcp.SseMcpToolAdapter.from_server_params", new_callable=AsyncMock) as mock_from_server_params:
#             mock_from_server_params.return_value = "mocked_adapter"
#
#             # Get the translation tool from the server
#             add_exclamation_adapter = await SseMcpToolAdapter.from_server_params(server_params, "add_exclamation")
#
#             # Assert the mocked method was called
#             mock_from_server_params.assert_called_once_with(server_params, "add_exclamation")
#
#     loop.run_until_complete(_test())

@pytest.fixture
def mock_sse_session() -> AsyncMock:
    session = AsyncMock(spec=ClientSession)
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock()
    session.list_tools = AsyncMock()
    return session


@pytest.fixture
def sample_sse_tool():
    return Tool(
        name="test_sse_tool",
        description="A test SSE tool",
        inputSchema={
            "type": "object",
            "properties": {"test_param": {"type": "string"}},
            "required": ["test_param"],
        },
    )


@validate_transaction_metrics(
    "test_agent_tracing:test_from_server_params_tracing",
    scoped_metrics=[("Function/autogen_ext.tools.mcp._sse:SseMcpToolAdapter.from_server_params/add_exclamation", 1)],
    rollup_metrics=[("Function/autogen_ext.tools.mcp._sse:SseMcpToolAdapter.from_server_params/add_exclamation", 1)],
    background_task=True,
)
@background_task()
def test_from_server_params_tracing(loop, mock_sse_session, monkeypatch, sample_sse_tool):
    async def _test():
        params = SseServerParams(url="http://test-url")
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_sse_session
        monkeypatch.setattr(
            "autogen_ext.tools.mcp._base.create_mcp_server_session",
            lambda *args, **kwargs: mock_context,  # type: ignore
        )

        mock_sse_session.list_tools.return_value.tools = [sample_sse_tool]

        adapter = await SseMcpToolAdapter.from_server_params(params, "test_sse_tool")

    loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_agent_tracing:test_from_server_params_tracing",
    scoped_metrics=[("Function/autogen_ext.tools.mcp._sse:SseMcpToolAdapter.from_server_params/add_exclamation", 1)],
    rollup_metrics=[("Function/autogen_ext.tools.mcp._sse:SseMcpToolAdapter.from_server_params/add_exclamation", 1)],
    background_task=True,
)
@background_task()
def test_on_messages_stream_tracing(loop):
    async def _test():


    loop.run_until_complete(_test())