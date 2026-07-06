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

from google.adk.agents import LlmAgent, ParallelAgent

MODEL = "gemini-3.5-flash"

PARALLEL_AGENT_NAME = "my_parallel"
LEFT_AGENT_NAME = "left"
RIGHT_AGENT_NAME = "right"

LEFT_INSTRUCTION = "Reply with the single word: Tokyo"
RIGHT_INSTRUCTION = "Reply with the single word: Berlin"

PARALLEL_PROMPT = "Begin."


def build_parallel():
    """Return a ParallelAgent with two independent LlmAgent children."""
    left = LlmAgent(name=LEFT_AGENT_NAME, model=MODEL, instruction=LEFT_INSTRUCTION)
    right = LlmAgent(name=RIGHT_AGENT_NAME, model=MODEL, instruction=RIGHT_INSTRUCTION)
    return ParallelAgent(name=PARALLEL_AGENT_NAME, sub_agents=[left, right])


parallel_workflow_agent_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": PARALLEL_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


parallel_left_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": LEFT_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


parallel_right_recorded_event = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": RIGHT_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
    },
)


parallel_recorded_events = [
    parallel_workflow_agent_recorded_event,
    parallel_left_recorded_event,
    parallel_right_recorded_event,
]

# For error tests, only the left child raises while the right completes concurrently.
# asyncio.TaskGroup wraps the left's ValueError into an ExceptionGroup, which
# propagates up and marks the parent workflow event error=True. The right child's event
# stays non-error.

parallel_workflow_agent_recorded_event_error = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": PARALLEL_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    },
)


parallel_left_recorded_event_error = (
    {"type": "LlmAgent"},
    {
        "id": None,
        "name": LEFT_AGENT_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "vendor": "google_adk",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    },
)


parallel_recorded_events_error = [
    parallel_workflow_agent_recorded_event_error,
    parallel_left_recorded_event_error,
    parallel_right_recorded_event,
]
