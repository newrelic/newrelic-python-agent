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

from google.adk.agents import LlmAgent, LoopAgent

MODEL = "gemini-3.5-flash"

LOOP_AGENT_NAME = "my_loop"
LOOPED_AGENT_NAME = "looped"
LOOP_MAX_ITERATIONS = 2

LOOPED_INSTRUCTION = "Reply with the single word: Ping"

LOOP_PROMPT = "Begin."


def build_loop():
    """Return a LoopAgent with one LlmAgent child and max_iterations=2."""
    looped = LlmAgent(name=LOOPED_AGENT_NAME, model=MODEL, instruction=LOOPED_INSTRUCTION)
    return LoopAgent(name=LOOP_AGENT_NAME, sub_agents=[looped], max_iterations=LOOP_MAX_ITERATIONS)


loop_workflow_agent_recorded_event = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": LOOP_AGENT_NAME,
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "google_adk",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]

loop_child_recorded_event = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": LOOPED_AGENT_NAME,
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "google_adk",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]

# TODO: validate_custom_events requires exactly one match per event, and
# the child runs twice in this loop. Since there are 2 identical evetns,
# the validator can't be used to validate the child events. Instead, the
# child is only validated at the span level via span counts.
loop_recorded_events = loop_workflow_agent_recorded_event


loop_workflow_agent_recorded_event_error = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": LOOP_AGENT_NAME,
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "google_adk",
            "ingest_source": "Python",
            "duration": None,
            "error": True,
        },
    )
]

loop_child_recorded_event_error = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": LOOPED_AGENT_NAME,
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "google_adk",
            "ingest_source": "Python",
            "duration": None,
            "error": True,
        },
    )
]

# For error tests the child raises on its first iteration and exits the entire loop
loop_recorded_events_error = loop_workflow_agent_recorded_event_error + loop_child_recorded_event_error
