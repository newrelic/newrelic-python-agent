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

from unittest.mock import AsyncMock

import pytest
from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams
from mcp import ClientSession, Tool
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

# Test setup derived from: https://github.com/microsoft/autogen/blob/main/python/packages/autogen-ext/tests/tools/test_mcp_tools.py
# autogen MIT license: https://github.com/microsoft/autogen/blob/main/LICENSE and
# https://github.com/microsoft/autogen/blob/main/LICENSE-CODE


@pytest.fixture
def mock_sse_session():
    session = AsyncMock(spec=ClientSession)
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock()
    session.list_tools = AsyncMock()
    return session


@pytest.fixture
def add_exclamation():
    return Tool(
        name="add_exclamation",
        description="A test SSE tool that adds an exclamation mark to a string",
        inputSchema={"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
    )


@validate_transaction_metrics(
    "test_mcp_tool_adapter:test_from_server_params_tracing",
    scoped_metrics=[("Llm/autogen_ext.tools.mcp._sse:SseMcpToolAdapter.from_server_params/add_exclamation", 1)],
    rollup_metrics=[("Llm/autogen_ext.tools.mcp._sse:SseMcpToolAdapter.from_server_params/add_exclamation", 1)],
    background_task=True,
)
@background_task()
def test_from_server_params_tracing(loop, mock_sse_session, monkeypatch, add_exclamation):
    async def _test():
        params = SseServerParams(url="http://test-url")
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_sse_session
        monkeypatch.setattr(
            "autogen_ext.tools.mcp._base.create_mcp_server_session", lambda *args, **kwargs: mock_context
        )

        mock_sse_session.list_tools.return_value.tools = [add_exclamation]

        adapter = await SseMcpToolAdapter.from_server_params(params, "add_exclamation")

    loop.run_until_complete(_test())
