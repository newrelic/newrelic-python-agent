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

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

MODEL = "gemini-3.5-flash"

PARENT_AGENT_NAME = "parent_agent"
# The child agent's name is automatically applied to AgentTool as well
CHILD_AGENT_NAME = AGENT_TOOL_NAME = "geo_specialist"

PARENT_INSTRUCTION = (
    "You are a routing agent. If the user asks a geography question (e.g. "
    f"about a country's capital), call the tool named '{AGENT_TOOL_NAME}' to "
    "delegate. Otherwise answer the user directly."
)
CHILD_INSTRUCTION = "Answer the user's geography question in one word."
CHILD_DESCRIPTION = "A geography specialist agent that answers geography questions in one word."

PROMPT = "What is the capital of France?"

EXPECTED_AGENT_TOOL_INPUT_STR = "{'request': 'What is the capital of France?'}"
EXPECTED_AGENT_TOOL_OUTPUT_STR = "{'result': 'Paris'}"


def build_agent_with_agent_tool():
    """Return a parent LlmAgent whose tools include [AgentTool(agent=child)]."""
    child = LlmAgent(name=CHILD_AGENT_NAME, model=MODEL, instruction=CHILD_INSTRUCTION, description=CHILD_DESCRIPTION)
    parent = LlmAgent(
        name=PARENT_AGENT_NAME, model=MODEL, instruction=PARENT_INSTRUCTION, tools=[AgentTool(agent=child)]
    )
    return parent


parent_agent_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": PARENT_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


child_agent_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": CHILD_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


agent_tool_recorded_event = (
    {"type": "LlmTool"},
    {
        "id": None,
        "run_id": None,
        "name": AGENT_TOOL_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "agent_name": PARENT_AGENT_NAME,
        "input": EXPECTED_AGENT_TOOL_INPUT_STR,
        "output": EXPECTED_AGENT_TOOL_OUTPUT_STR,
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)

agent_tool_recorded_events = [parent_agent_recorded_event, child_agent_recorded_event, agent_tool_recorded_event]


# Errors raised in the tool will propagate up through child and parent setting the error status on all spans.
parent_agent_recorded_event_error = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": PARENT_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    },
)


child_agent_recorded_event_error = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": CHILD_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    },
)


agent_tool_recorded_event_error = (
    {"type": "LlmTool"},
    {
        "id": None,
        "run_id": None,
        "name": AGENT_TOOL_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "agent_name": PARENT_AGENT_NAME,
        "input": EXPECTED_AGENT_TOOL_INPUT_STR,
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    },
)


agent_tool_recorded_events_error = [
    parent_agent_recorded_event_error,
    child_agent_recorded_event_error,
    agent_tool_recorded_event_error,
]
