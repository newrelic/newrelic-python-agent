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
from google.adk.workflow import START, Workflow

MODEL = "gemini-3.5-flash"

WORKFLOW_AGENT_NAME = "my_workflow"
WORKFLOW_STEP1_AGENT_NAME = "wf_step1"
WORKFLOW_STEP2_AGENT_NAME = "wf_step2"

WORKFLOW_STEP1_INSTRUCTION = "Reply with the single word: Paris"
WORKFLOW_STEP2_INSTRUCTION = "Reply with the single word: France"

WORKFLOW_PROMPT = "Begin."


def build_workflow():
    """Return a Workflow with two LlmAgent nodes chained START -> step1 -> step2."""
    step1 = LlmAgent(name=WORKFLOW_STEP1_AGENT_NAME, model=MODEL, instruction=WORKFLOW_STEP1_INSTRUCTION)
    step2 = LlmAgent(name=WORKFLOW_STEP2_AGENT_NAME, model=MODEL, instruction=WORKFLOW_STEP2_INSTRUCTION)
    return Workflow(name=WORKFLOW_AGENT_NAME, edges=[(START, step1, step2)])


workflow_step1_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": WORKFLOW_STEP1_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


workflow_step2_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": WORKFLOW_STEP2_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


workflow_recorded_events = [workflow_step1_recorded_event, workflow_step2_recorded_event]


# For error tests, step1 completes its full LLM round-trip normally and step2 raises an exception.

workflow_step2_recorded_event_error = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": WORKFLOW_STEP2_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    },
)

workflow_recorded_events_error = [workflow_step1_recorded_event, workflow_step2_recorded_event_error]
