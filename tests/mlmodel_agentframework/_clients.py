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

import os

import pytest

from ._test_agent import MODEL


@pytest.fixture(params=["bedrock"])  # Only testing on Bedrock for now, may expand later
def provider(request):
    # Fixture for a string representation of the connected LLM provider.
    # Used to construct the cassette file name.
    return request.param


@pytest.fixture
def client(provider, vcr_recording):
    _clients = {"openai": openai_client, "bedrock": bedrock_client, "anthropic": anthropic_client}
    return _clients[provider](vcr_recording)  # Lazily initialize the client


def openai_client(vcr_recording):
    from agent_framework.openai import OpenAIChatClient

    if vcr_recording:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY environment variable required.", allow_module_level=True)
    else:
        openai_api_key = os.environ["OPENAI_API_KEY"] = "NOT-A-REAL-SECRET"

    return OpenAIChatClient(model=MODEL, api_key=openai_api_key)


def anthropic_client(vcr_recording):
    from agent_framework.anthropic import AnthropicClient

    if vcr_recording:
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            pytest.skip("ANTHROPIC_API_KEY environment variable required.", allow_module_level=True)
    else:
        anthropic_api_key = os.environ["ANTHROPIC_API_KEY"] = "NOT-A-REAL-SECRET"

    return AnthropicClient(model=MODEL, api_key=anthropic_api_key)


def bedrock_client(vcr_recording):
    from agent_framework.amazon import BedrockChatClient

    if vcr_recording:
        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        if not (access_key and secret_key):
            pytest.skip(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables required.", allow_module_level=True
            )
    else:
        access_key = "NOT-A-REAL-SECRET"
        secret_key = "NOT-A-REAL-SECRET"

    return BedrockChatClient(model=MODEL, region="us-east-1", access_key=access_key, secret_key=secret_key)
