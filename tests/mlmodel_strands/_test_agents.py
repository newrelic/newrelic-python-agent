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

from ._mock_model_provider import MockedModelProvider


@tool
async def add_exclamation(message: str) -> str:
    """Adds an exclamation mark to the input message."""
    if "exc" in message:
        raise RuntimeError("Oops")
    return f"{message}!"


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
