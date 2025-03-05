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
STREAMED_RESPONSES_V1 = {
    "You are a world class algorithm for extracting information in structured formats.": [
        {
            "content-type": "text/event-stream",
            "openai-model": "gpt-3.5-turbo-0125",
            "openai-organization": "foobar-jtbczk",
            "openai-processing-ms": "511",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-remaining-requests": "196",
            "x-ratelimit-remaining-tokens": "39924",
            "x-ratelimit-reset-requests": "23m16.298s",
            "x-ratelimit-reset-tokens": "114ms",
            "x-request-id": "req_69c9ac5f95907fdb4af31572fd99537f",
        },
        200,
        [
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [
                    {"index": 0, "delta": {"role": "assistant", "content": ""}, "logprobs": None, "finish_reason": None}
                ],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": "The"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": " extracted"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [
                    {"index": 0, "delta": {"content": " information"}, "logprobs": None, "finish_reason": None}
                ],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": " from"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": " the"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": " input"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": ' "'}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": "Hello"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": ","}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": " world"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": '"'}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": " is"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": ' "'}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": "H"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": "elloworld"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {"content": '"'}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8uUiO2kRX1yl9fyniZCjJ6q3GN8wf",
                "object": "chat.completion.chunk",
                "created": 1708475128,
                "model": "gpt-3.5-turbo-0125",
                "system_fingerprint": "fp_69829325d0",
                "choices": [{"index": 0, "delta": {}, "logprobs": None, "finish_reason": "stop"}],
            },
        ],
    ]
}
RESPONSES_V1 = {
    "3923": [
        {
            "content-type": "application/json",
            "openai-model": "text-embedding-ada-002",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "26",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "3000",
            "x-ratelimit-limit-tokens": "1000000",
            "x-ratelimit-remaining-requests": "2999",
            "x-ratelimit-remaining-tokens": "999992",
            "x-ratelimit-reset-requests": "20ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_222ee158a955e783854f6e7cf52e6e5a",
        },
        200,
        {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": 0,
                    "embedding": "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",
                }
            ],
            "model": "text-embedding-ada-002",
            "usage": {"prompt_tokens": 8, "total_tokens": 8},
        },
    ],
    "10590": [
        {
            "content-type": "application/json",
            "openai-model": "text-embedding-ada-002",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "19",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "3000",
            "x-ratelimit-limit-tokens": "1000000",
            "x-ratelimit-remaining-requests": "2999",
            "x-ratelimit-remaining-tokens": "999998",
            "x-ratelimit-reset-requests": "20ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_f6e05c43962fe31877c469d6e15861ee",
        },
        200,
        {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": 0,
                    "embedding": "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",
                }
            ],
            "model": "text-embedding-ada-002",
            "usage": {"prompt_tokens": 1, "total_tokens": 1},
        },
    ],
    "You are a generator of quiz questions for a seminar. Use the following pieces of retrieved context to generate 5 multiple choice questions (A,B,C,D) on the subject matter. Use a three sentence maximum and keep the answer concise. Render the output as HTML\n\nWhat is 2 + 4?": [
        {
            "content-type": "application/json",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "4977",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "200000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "199912",
            "x-ratelimit-reset-requests": "8.64s",
            "x-ratelimit-reset-tokens": "26ms",
            "x-request-id": "req_942efbd5ead41ff093d2f8bfb7833fcb",
        },
        200,
        {
            "id": "chatcmpl-A0tPUPHiRvco7ONEyOMrW88Qk95vl",
            "object": "chat.completion",
            "created": 1724776360,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "```html\n<!DOCTYPE html>\n<html>\n<head>\n  <title>Math Quiz</title>\n</head>\n<body>\n  <h2>Math Quiz Questions</h2>\n  <ol>\n    <li>What is the result of 5 + 3?</li>\n      <ul>\n        <li>A) 7</li>\n        <li>B) 8</li>\n        <li>C) 9</li>\n        <li>D) 10</li>\n      </ul>\n    <li>What is the product of 6 x 7?</li>\n      <ul>\n        <li>A) 36</li>\n        <li>B) 42</li>\n        <li>C) 48</li>\n        <li>D) 56</li>\n      </ul>\n    <li>What is the square root of 64?</li>\n      <ul>\n        <li>A) 6</li>\n        <li>B) 7</li>\n        <li>C) 8</li>\n        <li>D) 9</li>\n      </ul>\n    <li>What is the result of 12 / 4?</li>\n      <ul>\n        <li>A) 2</li>\n        <li>B) 3</li>\n        <li>C) 4</li>\n        <li>D) 5</li>\n      </ul>\n    <li>What is the sum of 15 + 9?</li>\n      <ul>\n        <li>A) 22</li>\n        <li>B) 23</li>\n        <li>C) 24</li>\n        <li>D) 25</li>\n      </ul>\n  </ol>\n</body>\n</html>\n```",
                        "refusal": None,
                    },
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 73, "completion_tokens": 375, "total_tokens": 448},
            "system_fingerprint": None,
        },
    ],
    "You are a world class algorithm for extracting information in structured formats.": [
        {
            "content-type": "application/json",
            "openai-model": "gpt-3.5-turbo-1106",
            "openai-organization": "foobar-jtbczk",
            "openai-processing-ms": "749",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-limit-tokens_usage_based": "40000",
            "x-ratelimit-remaining-requests": "197",
            "x-ratelimit-remaining-tokens": "39929",
            "x-ratelimit-remaining-tokens_usage_based": "39929",
            "x-ratelimit-reset-requests": "16m17.764s",
            "x-ratelimit-reset-tokens": "106ms",
            "x-ratelimit-reset-tokens_usage_based": "106ms",
            "x-request-id": "f47e6e80fb796a56c05ad89c5d98609c",
        },
        200,
        {
            "id": "chatcmpl-8ckHXhZGwmPuqIIaKLbacUEq4SPq1",
            "object": "chat.completion",
            "created": 1704245063,
            "model": "gpt-3.5-turbo-1106",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "function_call": {"name": "output_formatter", "arguments": '{"name":"Sally","age":13}'},
                    },
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 159, "completion_tokens": 10, "total_tokens": 169},
            "system_fingerprint": "fp_772e8125bb",
        },
    ],
    "You are a world class algorithm for extracting information in structured formats with openai failures.": [
        {"content-type": "application/json; charset=utf-8", "x-request-id": "e58911d54d574647d36237e4e53c0f1a"},
        401,
        {
            "error": {
                "message": "Incorrect API key provided: No-exist. You can find your API key at https://platform.openai.com/account/api-keys.",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_api_key",
            }
        },
    ],
    "You are a helpful assistant who generates comma separated lists.\n    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.\n    ONLY return a comma separated list, and nothing more.": [
        {
            "Content-Type": "application/json",
            "openai-model": "gpt-3.5-turbo-0613",
            "openai-organization": "foobar-jtbczk",
            "openai-processing-ms": "488",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-limit-tokens_usage_based": "40000",
            "x-ratelimit-remaining-requests": "199",
            "x-ratelimit-remaining-tokens": "39921",
            "x-ratelimit-remaining-tokens_usage_based": "39921",
            "x-ratelimit-reset-requests": "7m12s",
            "x-ratelimit-reset-tokens": "118ms",
            "x-ratelimit-reset-tokens_usage_based": "118ms",
            "x-request-id": "f3de99e17ccc360430cffa243b74dcbd",
        },
        200,
        {
            "id": "chatcmpl-8XEjOPNHth7yS2jt1You3fEwB6w9i",
            "object": "chat.completion",
            "created": 1702932142,
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "red, blue, green, yellow, orange"},
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 60, "completion_tokens": 9, "total_tokens": 69},
            "system_fingerprint": None,
        },
    ],
    "9906": [
        {
            "content-type": "application/json",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "23",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "3000",
            "x-ratelimit-limit-tokens": "1000000",
            "x-ratelimit-remaining-requests": "2999",
            "x-ratelimit-remaining-tokens": "999996",
            "x-ratelimit-reset-requests": "20ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "058b2dd82590aa4145e97c2e59681f62",
        },
        200,
        {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": 0,
                    "embedding": "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",
                }
            ],
            "model": "text-embedding-ada-002-v2",
            "usage": {"prompt_tokens": 4, "total_tokens": 4},
        },
    ],
    "12833": [
        {
            "content-type": "application/json",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "26",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "3000",
            "x-ratelimit-limit-tokens": "1000000",
            "x-ratelimit-remaining-requests": "2999",
            "x-ratelimit-remaining-tokens": "999994",
            "x-ratelimit-reset-requests": "20ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "d5d71019880e25a94de58b927045a202",
        },
        200,
        {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": 0,
                    "embedding": "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",
                }
            ],
            "model": "text-embedding-ada-002-v2",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        },
    ],
}


@pytest.fixture(scope="session")
def simple_get(openai_version, extract_shortened_prompt):
    def _simple_get(self):
        content_len = int(self.headers.get("content-length"))
        content = json.loads(self.rfile.read(content_len).decode("utf-8"))
        stream = content.get("stream", False)
        prompt = extract_shortened_prompt(content)
        if not prompt:
            self.send_response(500)
            self.end_headers()
            self.wfile.write("Could not parse prompt.".encode("utf-8"))
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
            self.wfile.write(f"Unknown Prompt:\n{prompt}".encode("utf-8"))
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
            super(_MockExternalOpenAIServer, self).__init__(handler=handler, port=port, *args, **kwargs)

    return _MockExternalOpenAIServer


@pytest.fixture(scope="session")
def extract_shortened_prompt(openai_version):
    def _extract_shortened_prompt(content):
        _input = content.get("input", None)
        prompt = (_input and str(_input[0][0])) or content.get("messages")[0]["content"]
        return prompt

    return _extract_shortened_prompt


def get_openai_version():
    # Import OpenAI so that get package version can catpure the version from the
    # system module. OpenAI does not have a package version in v0.
    import openai

    return get_package_version_tuple("openai")


@pytest.fixture(scope="session")
def openai_version():
    return get_openai_version()


if __name__ == "__main__":
    _MockExternalOpenAIServer = MockExternalOpenAIServer()
    with MockExternalOpenAIServer() as server:
        print(f"MockExternalOpenAIServer serving on port {str(server.port)}")
        while True:
            pass  # Serve forever
