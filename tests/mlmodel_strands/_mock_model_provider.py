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

# Test setup derived from: https://github.com/strands-agents/sdk-python/blob/main/tests/fixtures/mocked_model_provider.py
# strands Apache 2.0 license: https://github.com/strands-agents/sdk-python/blob/main/LICENSE

import json
from typing import TypedDict

from strands.models import Model


class RedactionMessage(TypedDict):
    redactedUserContent: str
    redactedAssistantContent: str


class MockedModelProvider(Model):
    """A mock implementation of the Model interface for testing purposes.

    This class simulates a model provider by returning pre-defined agent responses
    in sequence. It implements the Model interface methods and provides functionality
    to stream mock responses as events.
    """

    def __init__(self, agent_responses):
        self.agent_responses = agent_responses
        self.index = 0

    def format_chunk(self, event):
        return event

    def format_request(self, messages, tool_specs=None, system_prompt=None):
        return None

    def get_config(self):
        pass

    def update_config(self, **model_config):
        pass

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        pass

    async def stream(self, messages, tool_specs=None, system_prompt=None):
        events = self.map_agent_message_to_events(self.agent_responses[self.index])
        for event in events:
            yield event

        self.index += 1

    def map_agent_message_to_events(self, agent_message):
        stop_reason = "end_turn"
        yield {"messageStart": {"role": "assistant"}}
        if agent_message.get("redactedAssistantContent"):
            yield {"redactContent": {"redactUserContentMessage": agent_message["redactedUserContent"]}}
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": agent_message["redactedAssistantContent"]}}}
            yield {"contentBlockStop": {}}
            stop_reason = "guardrail_intervened"
        else:
            for content in agent_message["content"]:
                if "reasoningContent" in content:
                    yield {"contentBlockStart": {"start": {}}}
                    yield {"contentBlockDelta": {"delta": {"reasoningContent": content["reasoningContent"]}}}
                    yield {"contentBlockStop": {}}
                if "text" in content:
                    yield {"contentBlockStart": {"start": {}}}
                    yield {"contentBlockDelta": {"delta": {"text": content["text"]}}}
                    yield {"contentBlockStop": {}}
                if "toolUse" in content:
                    stop_reason = "tool_use"
                    yield {
                        "contentBlockStart": {
                            "start": {
                                "toolUse": {
                                    "name": content["toolUse"]["name"],
                                    "toolUseId": content["toolUse"]["toolUseId"],
                                }
                            }
                        }
                    }
                    yield {
                        "contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(content["toolUse"]["input"])}}}
                    }
                    yield {"contentBlockStop": {}}

        yield {"messageStop": {"stopReason": stop_reason}}
