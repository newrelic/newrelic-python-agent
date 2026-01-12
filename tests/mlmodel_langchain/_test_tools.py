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


# add_exclamation is implemented 4 different ways, but aliased to the same name.
# The agent will end up reporting identical data for all of them.
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


@tool(name="add_exclamation")
async def add_exclamation_agen(message: str) -> str:
    """Adds an exclamation mark to the input message."""
    if "exc" in message:
        raise RuntimeError("Oops")
    yield f"{message}!"


@pytest.fixture(scope="session", params=["sync_tool", "async_tool", "agen_tool"])
def add_exclamation(request):
    if request.param == "sync_tool":
        return add_exclamation_sync
    elif request.param == "async_tool":
        return add_exclamation_async
    elif request.param == "agen_tool":
        return add_exclamation_agen
    else:
        raise NotImplementedError
