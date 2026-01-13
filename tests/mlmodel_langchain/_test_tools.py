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
from langchain.tools import tool


@tool("add_exclamation")
def add_exclamation_sync(message: str) -> str:
    """Adds an exclamation mark to the input message."""
    if "exc" in message:
        raise RuntimeError("Oops")
    return f"{message}!"


@tool("add_exclamation")
async def add_exclamation_async(message: str) -> str:
    """Adds an exclamation mark to the input message."""
    if "exc" in message:
        raise RuntimeError("Oops")
    return f"{message}!"


@pytest.fixture(scope="session", params=["sync_tool", "async_tool"])
def tool_type(request):
    return request.param


@pytest.fixture(scope="session")
def tool_method_name(tool_type):
    return "run" if tool_type == "sync_tool" else "arun"


@pytest.fixture(scope="session")
def add_exclamation(tool_type, exercise_agent):
    if tool_type == "sync_tool":
        return add_exclamation_sync
    elif tool_type == "async_tool":
        if exercise_agent._called_method in {"invoke", "stream"}:
            pytest.skip("Async tools cannot be invoked synchronously.")
        return add_exclamation_async
    else:
        raise NotImplementedError
