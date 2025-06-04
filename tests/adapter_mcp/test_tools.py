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
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.server.server import FastMCP
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@pytest.fixture
def fastmcp_server():
    server = FastMCP("Test Tools")

    @server.tool()
    def add_exclamation(phrase):
        return f"{phrase}!"

    return server


@validate_transaction_metrics(
    "test_tools:test_tool_tracing",
    scoped_metrics=[("Llm/tool/MCP/mcp.client.session:ClientSession.call_tool/add_exclamation", 1)],
    rollup_metrics=[("Llm/tool/MCP/mcp.client.session:ClientSession.call_tool/add_exclamation", 1)],
    background_task=True,
)
@background_task()
def test_tool_tracing(loop, fastmcp_server):
    async def _test():
        async with Client(transport=FastMCPTransport(fastmcp_server)) as client:
            # Call the MCP tool, so we can validate the trace naming is correct.
            result = await client.call_tool("add_exclamation", {"phrase": "Python is awesome"})

            content = str(result[0])
            assert "Python is awesome!" in content

    loop.run_until_complete(_test())
