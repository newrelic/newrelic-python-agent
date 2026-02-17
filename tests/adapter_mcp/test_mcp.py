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
from mcp.server.fastmcp.tools import ToolManager
from testing_support.ml_testing_utils import disabled_ai_monitoring_settings
from testing_support.validators.validate_function_not_called import validate_function_not_called
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@pytest.fixture
def fastmcp_server():
    server = FastMCP("Test Tools")

    @server.tool()
    def add_exclamation(phrase):
        return f"{phrase}!"

    @server.resource("greeting://{name}")
    def get_greeting(name):
        return f"Hello, {name}!"

    @server.resource("files:///home/user/documents/{filename}")
    def get_file(filename):
        return f"Hello, Python! You requested the file: {filename}."

    @server.resource("postgres://python/customers/schema")
    def get_db_info():
        return "Hello, Python!"

    @server.prompt()
    def echo_prompt(message: str):
        return f"Echo this message: {message}"

    return server


@validate_transaction_metrics(
    "test_mcp:test_tool_tracing_via_client_session",
    scoped_metrics=[("Llm/tool/MCP/mcp.client.session:ClientSession.call_tool/add_exclamation", 1)],
    rollup_metrics=[("Llm/tool/MCP/mcp.client.session:ClientSession.call_tool/add_exclamation", 1)],
    background_task=True,
)
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
@background_task()
def test_tool_tracing_via_client_session(loop, fastmcp_server):
    async def _test():
        async with Client(transport=FastMCPTransport(fastmcp_server)) as client:
            # Call the MCP tool, so we can validate the trace naming is correct.
            result = await client.call_tool("add_exclamation", {"phrase": "Python is awesome"})
            content = str(result.content[0])
        assert "Python is awesome!" in content

    loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_mcp:test_tool_tracing_via_tool_manager",
    scoped_metrics=[("Llm/tool/MCP/mcp.server.fastmcp.tools.tool_manager:ToolManager.call_tool/add_exclamation", 1)],
    rollup_metrics=[("Llm/tool/MCP/mcp.server.fastmcp.tools.tool_manager:ToolManager.call_tool/add_exclamation", 1)],
    background_task=True,
)
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
@background_task()
def test_tool_tracing_via_tool_manager(loop):
    async def _test():
        def add_exclamation(phrase):
            return f"{phrase}!"

        manager = ToolManager()
        manager.add_tool(add_exclamation)
        result = await manager.call_tool("add_exclamation", {"phrase": "Python is awesome"})
        assert result == "Python is awesome!"

    loop.run_until_complete(_test())


# Separate out the test function to work with the transaction metrics validator
def run_read_resources(loop, fastmcp_server, resource_uri):
    async def _test():
        async with Client(transport=FastMCPTransport(fastmcp_server)) as client:
            result = await client.read_resource(resource_uri)
            content = str(result[0])
        assert "Hello, Python!" in content

    loop.run_until_complete(_test())


@pytest.mark.parametrize(
    "resource_uri",
    ("greeting://Python", "files:///home/user/documents/python.pdf", "postgres://python/customers/schema"),
)
def test_resource_tracing(loop, fastmcp_server, resource_uri):
    resource_scheme = resource_uri.split(":/")[0]

    @validate_transaction_metrics(
        "test_mcp:test_resource_tracing.<locals>._test",
        scoped_metrics=[(f"Llm/resource/MCP/mcp.client.session:ClientSession.read_resource/{resource_scheme}", 1)],
        rollup_metrics=[(f"Llm/resource/MCP/mcp.client.session:ClientSession.read_resource/{resource_scheme}", 1)],
        background_task=True,
    )
    @background_task()
    def _test():
        run_read_resources(loop, fastmcp_server, resource_uri)

    _test()


@validate_transaction_metrics(
    "test_mcp:test_prompt_tracing",
    scoped_metrics=[("Llm/prompt/MCP/mcp.client.session:ClientSession.get_prompt/echo_prompt", 1)],
    rollup_metrics=[("Llm/prompt/MCP/mcp.client.session:ClientSession.get_prompt/echo_prompt", 1)],
    background_task=True,
)
@background_task()
def test_prompt_tracing(loop, fastmcp_server):
    async def _test():
        async with Client(transport=FastMCPTransport(fastmcp_server)) as client:
            result = await client.get_prompt("echo_prompt", {"message": "Python is cool"})

            content = str(result)
        assert "Python is cool" in content

    loop.run_until_complete(_test())


@disabled_ai_monitoring_settings
@validate_function_not_called("newrelic.api.function_trace", "FunctionTrace.__enter__")
@background_task()
def test_tool_tracing_aim_disabled(loop, fastmcp_server):
    async def _test():
        async with Client(transport=FastMCPTransport(fastmcp_server)) as client:
            # Call the MCP tool, so we can validate the trace naming is correct.
            result = await client.call_tool("add_exclamation", {"phrase": "Python is awesome"})
            content = str(result.content[0])
        assert "Python is awesome!" in content

    loop.run_until_complete(_test())


@disabled_ai_monitoring_settings
@validate_function_not_called("newrelic.api.function_trace", "FunctionTrace.__enter__")
@background_task()
def test_resource_tracing_aim_disabled(loop, fastmcp_server):
    run_read_resources(loop, fastmcp_server, "greeting://Python")


@disabled_ai_monitoring_settings
@validate_function_not_called("newrelic.api.function_trace", "FunctionTrace.__enter__")
@background_task()
def test_prompt_tracing_aim_disabled(loop, fastmcp_server):
    async def _test():
        async with Client(transport=FastMCPTransport(fastmcp_server)) as client:
            result = await client.get_prompt("echo_prompt", {"message": "Python is cool"})

            content = str(result)
        assert "Python is cool" in content

    loop.run_until_complete(_test())
