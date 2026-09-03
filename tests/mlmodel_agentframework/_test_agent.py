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
from agent_framework import Agent

MODEL = "us.amazon.nova-2-lite-v1:0"
AGENT_NAME = "my_agent"
AGENT_INSTRUCTION = "Answer the user's question in one word."
PROMPT = "What is the capital of France?"


@pytest.fixture
def build_agent(client):
    def _build_agent(tools=None):
        """Return an LlmAgent with no tools by default."""
        return Agent(client=client, name=AGENT_NAME, instructions=AGENT_INSTRUCTION, tools=tools or [])

    return _build_agent


@pytest.fixture(params=[False, True], ids=["ResponseStandard", "ResponseStreaming"])
def exercise_agent(loop, request):
    is_streaming = request.param

    def _exercise_agent(agent, prompt):
        async def _exercise():
            if is_streaming:
                response_stream = agent.run(prompt, stream=True)
                async for _ in response_stream:
                    pass
                return await response_stream.get_final_response()
            else:
                return await agent.run(prompt)

        return loop.run_until_complete(_exercise())

    return _exercise_agent


agent_recorded_event = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": AGENT_NAME,
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "agentframework",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]

agent_recorded_event_error = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": AGENT_NAME,
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "agentframework",
            "ingest_source": "Python",
            "duration": None,
            "error": True,
        },
    )
]
