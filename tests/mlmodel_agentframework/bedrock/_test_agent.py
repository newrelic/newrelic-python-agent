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

from agent_framework import Agent

MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"
AGENT_NAME = "my_agent"
AGENT_INSTRUCTION = "Answer the user's question in one word."
PROMPT = "What is the capital of France?"


def build_agent(client, tools=None):
    return Agent(client=client, name=AGENT_NAME, instructions=AGENT_INSTRUCTION, tools=tools)


# TODO: This will house the expected events once Agent Framework instrumentation is written.

# agent_recorded_event = [
#     (
#         {"type": "LlmAgent"},
#         {
#             "id": None,
#             "name": AGENT_NAME,
#             "span_id": None,
#             "trace_id": "trace-id",
#             "vendor": "agentframework",
#             "ingest_source": "Python",
#             "duration": None,
#         },
#     )
# ]

# agent_recorded_event_error = [
#     (
#         {"type": "LlmAgent"},
#         {
#             "id": None,
#             "name": AGENT_NAME,
#             "span_id": None,
#             "trace_id": "trace-id",
#             "vendor": "agentframework",
#             "ingest_source": "Python",
#             "duration": None,
#             "error": True,
#         },
#     )
# ]
