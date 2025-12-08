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
from strands import Agent, tool
from strands.multiagent.graph import GraphBuilder

from ._mock_model_provider import MockedModelProvider


@pytest.fixture
def math_model():
    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {"text": "I'll calculate the sum of 15 and 27 for you."},
                    {"toolUse": {"name": "calculate_sum", "toolUseId": "123", "input": {"a": 15, "b": 27}}},
                ],
            },
            {"role": "assistant", "content": [{"text": "The sum of 15 and 27 is 42."}]},
        ]
    )
    return model


@pytest.fixture
def analysis_model():
    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {"text": "I'll validate the calculation result of 42 from the calculator."},
                    {"toolUse": {"name": "analyze_result", "toolUseId": "456", "input": {"value": 42}}},
                ],
            },
            {
                "role": "assistant",
                "content": [{"text": "The calculation is correct, and 42 is a positive integer result."}],
            },
        ]
    )
    return model


# Example tool for testing purposes
@tool
async def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two numbers."""
    return a + b


@tool
async def analyze_result(value: int) -> str:
    """Analyze a numeric result."""
    return f"The result {value} is {'positive' if value > 0 else 'zero or negative'}"


@pytest.fixture
def math_agent(math_model):
    return Agent(name="math_agent", model=math_model, tools=[calculate_sum])


@pytest.fixture
def analysis_agent(analysis_model):
    return Agent(name="analysis_agent", model=analysis_model, tools=[analyze_result])


@pytest.fixture
def agent_graph(math_agent, analysis_agent):
    # Build graph
    builder = GraphBuilder()
    builder.add_node(math_agent, "math")
    builder.add_node(analysis_agent, "analysis")
    builder.add_edge("math", "analysis")
    builder.set_entry_point("math")

    return builder.build()
