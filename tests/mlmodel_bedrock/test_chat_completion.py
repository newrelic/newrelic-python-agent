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

import json

import pytest

_test_bedrock_chat_completion_prompt = "Write me a blog about making strong business decisions as a leader."


@pytest.mark.parametrize(
    "model_id,payload",
    [
        ("amazon.titan-text-express-v1", {"inputText": "Command: %s\n\nBlog:"}),
        ("anthropic.claude-instant-v1", {"prompt": "Human: %s\n\nAssistant:", "max_tokens_to_sample": 500}),
        ("ai21.j2-mid-v1", {"prompt": "%s", "maxTokens": 200}),
        ("cohere.command-text-v14", {"prompt": "%s", "max_tokens": 200, "temperature": 0.75}),
    ],
)
def test_bedrock_chat_completion(bedrock_server, model_id, payload):
    body = json.dumps(payload) % _test_bedrock_chat_completion_prompt
    response = bedrock_server.invoke_model(
        body=body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json",
    )
    response_body = json.loads(response.get("body").read())
    assert response_body
