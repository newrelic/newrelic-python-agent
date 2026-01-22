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
from strands import tool
from strands.tools import PythonAgentTool

from ._mock_model_provider import MockedModelProvider


# add_exclamation is implemented 5 different ways, but aliased to the same name.
# The agent will end up reporting identical data for all of them.
@tool(name="add_exclamation")
def add_exclamation_sync(message: str) -> str:
    """Adds an exclamation mark to the input message."""
    if "exc" in message:
        raise RuntimeError("Oops")
    return f"{message}!"


@tool(name="add_exclamation")
async def add_exclamation_async(message: str) -> str:
    """Adds an exclamation mark to the input message."""
    if "exc" in message:
        raise RuntimeError("Oops")
    return f"{message}!"


@tool(name="add_exclamation")
async def add_exclamation_agen(message: str) -> str:
    """Adds an exclamation mark to the input message."""
    if "exc" in message:
        raise RuntimeError("Oops")
    yield f"{message}!"


def add_exclamation_sync_PythonAgentTool(tool_use, **invocation_state):
    """Adds an exclamation mark to the input message."""
    message = tool_use["input"]["message"]
    if "exc" in message:
        raise RuntimeError("Oops")
    return {"status": "success", "toolUseId": tool_use["toolUseId"], "content": [{"text": f"{message}!"}]}


async def add_exclamation_async_PythonAgentTool(tool_use, **invocation_state):
    """Adds an exclamation mark to the input message."""
    message = tool_use["input"]["message"]
    if "exc" in message:
        raise RuntimeError("Oops")
    return {"status": "success", "toolUseId": tool_use["toolUseId"], "content": [{"text": f"{message}!"}]}


_tool_spec = {
    "name": "add_exclamation",
    "description": "Adds an exclamation mark to the input message.",
    "inputSchema": {
        "json": {
            "properties": {"message": {"description": "Parameter message", "type": "string"}},
            "required": ["message"],
            "type": "object",
        }
    },
}
_tool_spec = add_exclamation_sync._tool_spec


@pytest.fixture(
    scope="session", params=["sync_@tool", "async_@tool", "agen_@tool", "sync_PythonAgentTool", "async_PythonAgentTool"]
)
def add_exclamation(request):
    if request.param == "sync_@tool":
        return add_exclamation_sync
    elif request.param == "async_@tool":
        return add_exclamation_async
    elif request.param == "agen_@tool":
        return add_exclamation_agen
    elif request.param == "sync_PythonAgentTool":
        return PythonAgentTool(
            tool_name="add_exclamation", tool_spec=_tool_spec, tool_func=add_exclamation_sync_PythonAgentTool
        )
    elif request.param == "async_PythonAgentTool":
        return PythonAgentTool(
            tool_name="add_exclamation", tool_spec=_tool_spec, tool_func=add_exclamation_async_PythonAgentTool
        )
    else:
        raise NotImplementedError


@pytest.fixture
def single_tool_model():
    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling add_exclamation tool"},
                    {"toolUse": {"name": "add_exclamation", "toolUseId": "123", "input": {"message": "Hello"}}},
                ],
            },
            {"role": "assistant", "content": [{"text": "Success!"}]},
        ]
    )
    return model


@pytest.fixture
def single_tool_model_error():
    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling add_exclamation tool"},
                    # Set arguments to an invalid type to trigger error in tool
                    {"toolUse": {"name": "add_exclamation", "toolUseId": "123", "input": {"message": "exc"}}},
                ],
            },
            {"role": "assistant", "content": [{"text": "Success!"}]},
        ]
    )
    return model
