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

MODEL = "gemini-3.5-flash"

PARENT_AGENT_NAME = "parent_agent"
CHILD_AGENT_NAME = "child_agent"

PARENT_INSTRUCTION = (
    "You are a routing agent. If the user asks a geography question (e.g. "
    f"about a country's capital), transfer to the agent named '{CHILD_AGENT_NAME}' "
    "using the transfer_to_agent tool. Otherwise, answer the user directly."
)
CHILD_INSTRUCTION = "Answer the user's geography question in one word."

PROMPT = "What is the capital of France?"

EXPECTED_TRANSFER_INPUT_STR = f"{{'agent_name': '{CHILD_AGENT_NAME}'}}"
EXPECTED_TRANSFER_OUTPUT_STR = "{'result': None}"


def build_sub_agent():
    """Return a parent LlmAgent with a child LlmAgent registered via sub_agents."""
    child = LlmAgent(name=CHILD_AGENT_NAME, model=MODEL, instruction=CHILD_INSTRUCTION)
    parent = LlmAgent(name=PARENT_AGENT_NAME, model=MODEL, instruction=PARENT_INSTRUCTION, sub_agents=[child])
    return parent


parent_recorded_event = (
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


child_recorded_event = (
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


# ADK invokes its built-in transfer_to_agent tool function,so we capture
# an LlmTool event for it. agent_name is the parent agent which issued the
# tool call, and name is the tool name (transfer_to_agent).
transfer_to_agent_recorded_event = (
    {"type": "LlmTool"},
    {
        "id": None,
        "run_id": None,
        "name": "transfer_to_agent",
        "span_id": None,
        "trace_id": "trace-id",
        "agent_name": PARENT_AGENT_NAME,
        "input": EXPECTED_TRANSFER_INPUT_STR,
        "output": EXPECTED_TRANSFER_OUTPUT_STR,
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


sub_agent_recorded_event = [parent_recorded_event, child_recorded_event, transfer_to_agent_recorded_event]


# For error tests, the parent finishes its first turn normally with
# a tool call and does not see an error. The tool call also completes
# normally by initiating the transfer. The child raises an exception
# during its turn, so it is the only event that sees the error.

parent_recorded_event_error = parent_recorded_event

child_recorded_event_error = (
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


sub_agent_recorded_event_error = [
    parent_recorded_event_error,
    child_recorded_event_error,
    transfer_to_agent_recorded_event,
]
