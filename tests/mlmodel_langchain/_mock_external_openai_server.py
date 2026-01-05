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
from testing_support.mock_external_http_server import MockExternalHTTPServer

from newrelic.common.package_version_utils import get_package_version_tuple

# This defines an external server test apps can make requests to instead of
# the real OpenAI backend. This provides 3 features:
#
# 1) This removes dependencies on external websites.
# 2) Provides a better mechanism for making an external call in a test app than
#    simple calling another endpoint the test app makes available because this
#    server will not be instrumented meaning we don't have to sort through
#    transactions to separate the ones created in the test app and the ones
#    created by an external call.
# 3) This app runs on a separate thread meaning it won't block the test app.
STREAMED_RESPONSES_V1 = {}
   
RESPONSES_V1 = {
    'system: You are a text manipulation algorithm. | user: Use a tool to add an exclamation to the word "Hello"': [
        {
            "content-type": "application/json",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "324",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "50000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "49999974",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_619548c272db4f1ab380b83de9fdedef",
        },
        200,
        {
            "id": "chatcmpl-CukvsGfSQihNO9I3FTqaNKERWtUca",
            "object": "chat.completion",
            "created": 1767642812,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_ymnsNurMgr3atFVr7BnJ2XYK",
                                "type": "function",
                                "function": {"name": "add_exclamation", "arguments": '{"message":"Hello"}'},
                            }
                        ],
                        "refusal": None,
                        "annotations": [],
                    },
                    "logprobs": None,
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 70,
                "completion_tokens": 15,
                "total_tokens": 85,
                "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0},
                "completion_tokens_details": {
                    "reasoning_tokens": 0,
                    "audio_tokens": 0,
                    "accepted_prediction_tokens": 0,
                    "rejected_prediction_tokens": 0,
                },
            },
            "service_tier": "default",
            "system_fingerprint": None,
        },
    ],
    'system: You are a text manipulation algorithm. | user: Use a tool to add an exclamation to the word "Hello" | assistant: None | tool: Hello!': [
        {
            "content-type": "application/json",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "751",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "50000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "49999970",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_e9add199e2c543f1b0f1dc5318690171",
        },
        200,
        {
            "id": "chatcmpl-CukvtgYHPS8HRHqCQiQgQrs7a2Tx1",
            "object": "chat.completion",
            "created": 1767642813,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": 'The word "Hello" with an exclamation mark added is "Hello!"',
                        "refusal": None,
                        "annotations": [],
                    },
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 96,
                "completion_tokens": 16,
                "total_tokens": 112,
                "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0},
                "completion_tokens_details": {
                    "reasoning_tokens": 0,
                    "audio_tokens": 0,
                    "accepted_prediction_tokens": 0,
                    "rejected_prediction_tokens": 0,
                },
            },
            "service_tier": "default",
            "system_fingerprint": None,
        },
    ],
}


@pytest.fixture(scope="session")
def simple_get():
    def _simple_get(self):
        content_len = int(self.headers.get("content-length"))
        content = json.loads(self.rfile.read(content_len).decode("utf-8"))
        stream = content.get("stream", False)
        prompt = extract_shortened_prompt(content)
        if not prompt:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Could not parse prompt.")
            return

        headers, response = ({}, "")

        mocked_responses = RESPONSES_V1
        if stream:
            mocked_responses = STREAMED_RESPONSES_V1

        for k, v in mocked_responses.items():
            if prompt.startswith(k):
                headers, status_code, response = v
                break
        else:  # If no matches found
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Unknown Prompt:\n{prompt}".encode())
            return

        # Send response code
        self.send_response(status_code)

        # Send headers
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()

        # Send response body
        if stream and status_code < 400:
            for resp in response:
                data = json.dumps(resp).encode("utf-8")
                if prompt == "Stream parsing error.":
                    # Force a parsing error by writing an invalid streamed response.
                    self.wfile.write(b"data: %s" % data)
                else:
                    self.wfile.write(b"data: %s\n\n" % data)
        else:
            self.wfile.write(json.dumps(response).encode("utf-8"))
        return

    return _simple_get


@pytest.fixture(scope="session")
def MockExternalOpenAIServer(simple_get):
    class _MockExternalOpenAIServer(MockExternalHTTPServer):
        # To use this class in a test one needs to start and stop this server
        # before and after making requests to the test app that makes the external
        # calls.

        def __init__(self, handler=simple_get, port=None, *args, **kwargs):
            super().__init__(handler=handler, port=port, *args, **kwargs)  # noqa: B026

    return _MockExternalOpenAIServer


def extract_shortened_prompt(content):
    _input = content.get("input", None)
    if _input:
        return str(_input[0][0])

    # Transform all input messages into a single prompt
    messages = content.get("messages")
    prompt = [f"{message['role']}: {message['content']}" for message in messages]
    return " | ".join(prompt)


if __name__ == "__main__":
    _MockExternalOpenAIServer = MockExternalOpenAIServer()
    with MockExternalOpenAIServer() as server:
        print(f"MockExternalOpenAIServer serving on port {server.port!s}")
        while True:
            pass  # Serve forever
