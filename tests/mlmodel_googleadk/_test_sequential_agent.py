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

from google.adk.agents import LlmAgent, SequentialAgent

MODEL = "gemini-3.5-flash"

SEQUENTIAL_AGENT_NAME = "my_sequential"
STEP1_AGENT_NAME = "step1"
STEP2_AGENT_NAME = "step2"

STEP1_INSTRUCTION = "Reply with the single word: Paris"
STEP2_INSTRUCTION = "Reply with the single word: France"

SEQUENTIAL_PROMPT = "Begin."


def build_sequential():
    """Return a SequentialAgent with two LlmAgent children run in order."""
    step1 = LlmAgent(name=STEP1_AGENT_NAME, model=MODEL, instruction=STEP1_INSTRUCTION)
    step2 = LlmAgent(name=STEP2_AGENT_NAME, model=MODEL, instruction=STEP2_INSTRUCTION)
    return SequentialAgent(name=SEQUENTIAL_AGENT_NAME, sub_agents=[step1, step2])


sequential_workflow_agent_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": SEQUENTIAL_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


sequential_step1_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": STEP1_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


sequential_step2_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": STEP2_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


sequential_recorded_events = [
    sequential_workflow_agent_recorded_event,
    sequential_step1_recorded_event,
    sequential_step2_recorded_event,
]


# For the error tests, step1 raises during iteration, causing both the parent and child
# events to see the error. The parent terminates from the exception and step2 never runs.

sequential_workflow_agent_recorded_event_error = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": SEQUENTIAL_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    },
)


sequential_step1_recorded_event_error = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": STEP1_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    },
)


sequential_recorded_events_error = [
    sequential_workflow_agent_recorded_event_error,
    sequential_step1_recorded_event_error,
]
