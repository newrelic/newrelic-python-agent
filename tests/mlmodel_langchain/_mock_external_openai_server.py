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
    "system: You are a world class algorithm for extracting information in structured formats. | user: Use the given format to extract information from the following input: Hello, world | user: Tip: Make sure to answer in the correct format": [
        {
            "content-type": "text/event-stream; charset=utf-8",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "440",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "50000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "49999942",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_1addfc2e713648af834cb9992fd417d7",
        },
        200,
        [
            {
                "id": "chatcmpl-CvUIm4qNNuiHpumRpuX0HISeNKViC",
                "object": "chat.completion.chunk",
                "created": 1767817212,
                "model": "gpt-3.5-turbo-0125",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": "", "refusal": None},
                        "logprobs": None,
                        "finish_reason": None,
                    }
                ],
                "usage": None,
                "obfuscation": "HeQWMY8H",
            },
            {
                "id": "chatcmpl-CvUIm4qNNuiHpumRpuX0HISeNKViC",
                "object": "chat.completion.chunk",
                "created": 1767817212,
                "model": "gpt-3.5-turbo-0125",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": "Hello,"}, "logprobs": None, "finish_reason": None}],
                "usage": None,
                "obfuscation": "DferQO2zD",
            },
            {
                "id": "chatcmpl-CvUIm4qNNuiHpumRpuX0HISeNKViC",
                "object": "chat.completion.chunk",
                "created": 1767817212,
                "model": "gpt-3.5-turbo-0125",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " world!"}, "logprobs": None, "finish_reason": None}],
                "usage": None,
                "obfuscation": "LlLJvKqz",
            },
            {
                "id": "chatcmpl-CvUIm4qNNuiHpumRpuX0HISeNKViC",
                "object": "chat.completion.chunk",
                "created": 1767817212,
                "model": "gpt-3.5-turbo-0125",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {}, "logprobs": None, "finish_reason": "stop"}],
                "usage": None,
                "obfuscation": "Qzvy",
            },
            {
                "id": "chatcmpl-CvUIm4qNNuiHpumRpuX0HISeNKViC",
                "object": "chat.completion.chunk",
                "created": 1767817212,
                "model": "gpt-3.5-turbo-0125",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [],
                "usage": {
                    "prompt_tokens": 96,
                    "completion_tokens": 24,
                    "total_tokens": 120,
                    "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0},
                    "completion_tokens_details": {
                        "reasoning_tokens": 0,
                        "audio_tokens": 0,
                        "accepted_prediction_tokens": 0,
                        "rejected_prediction_tokens": 0,
                    },
                },
                "obfuscation": "NzeDrNhe",
            },
        ],
    ]
}
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
    'system: You are a text manipulation algorithm. | user: Use a tool to add an exclamation to the word "exc"': [
        {
            "content-type": "application/json",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "767",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "50000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "49999975",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_27d106351bab9878a3969f23108cd4c6",
        },
        200,
        {
            "id": "chatcmpl-CxGq2dnBYh5JR5o4OANlkHgBhuxfK",
            "object": "chat.completion",
            "created": 1768242114,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_blmqxOaZvxUtgB0JVLXYnEu1",
                                "type": "function",
                                "function": {"name": "add_exclamation", "arguments": '{"message":"exc"}'},
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
    "system: You are a helpful assistant who generates a random first name. A user will pass in a first letter, and you should generate a name that starts with that first letter. | user: M": [
        {
            "content-type": "application/json",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "236",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "50000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "49999955",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_58e5f91c0c3d4c2c9b6ee9ad8c4e8961",
        },
        200,
        {
            "id": "chatcmpl-CxGtBIjrsLMSkCUPSLOlAiHFxLz7A",
            "object": "chat.completion",
            "created": 1768242309,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Milo", "refusal": None, "annotations": []},
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 46,
                "completion_tokens": 2,
                "total_tokens": 48,
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
    "system: You are a helpful assistant who generates comma separated lists.\n    A user will pass in a category, and you should generate 5 objects in that category in a comma separated list.\n    ONLY return a comma separated list, and nothing more. | user: colors": [
        {
            "content-type": "application/json",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "289",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "50000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "49999935",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_fbc7bb2ab3e149c1845699cfea9403d4",
        },
        200,
        {
            "id": "chatcmpl-CxGyV8CzGN80ByzFb4wN1hwGktOKD",
            "object": "chat.completion",
            "created": 1768242639,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "red, blue, green, yellow, orange",
                        "refusal": None,
                        "annotations": [],
                    },
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 60,
                "completion_tokens": 9,
                "total_tokens": 69,
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
    "system: You are a world class algorithm for extracting information in structured formats. | user: Use the given format to extract information from the following input: Sally is 13 | user: Tip: Make sure to answer in the correct format": [
        {
            "content-type": "application/json",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "201",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "50000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "49999944",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_40a68eb08b684844b1e1f2253c85f00c",
        },
        200,
        {
            "id": "chatcmpl-CxGyZUlLnBXQkOnJyJNSlshVXdOwQ",
            "object": "chat.completion",
            "created": 1768242643,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "function_call": {"name": "output_formatter", "arguments": '{"name":"Sally","age":13}'},
                        "refusal": None,
                        "annotations": [],
                    },
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 159,
                "completion_tokens": 10,
                "total_tokens": 169,
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
    "system: You are a world class algorithm for extracting information in structured formats with openai failures. | user: Use the given format to extract information from the following input: Sally is 13 | user: Tip: Make sure to answer in the correct format": [
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
    "system: You are a generator of quiz questions for a seminar. Use the following pieces of retrieved context to generate 5 multiple choice questions (A,B,C,D) on the subject matter. Use a three sentence maximum and keep the answer concise. Render the output as HTML\n\nWhat is 2 + 4? | user: math": [
        {
            "content-type": "application/json",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "2029",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "50000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "49999927",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_008a31c6023e42c9ae640eae2ae3b5ad",
        },
        200,
        {
            "id": "chatcmpl-CxfJTw2pCnRMvza9LZyE8qitryqFC",
            "object": "chat.completion",
            "created": 1768336195,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "```html\n<!DOCTYPE html>\n<html>\n<head>\n  <title>Math Quiz</title>\n</head>\n<body>\n  <h2>Math Quiz Questions</h2>\n  <ol>\n    <li>What is the result of 5 + 3?</li>\n      <ul>\n        <li>A) 7</li>\n        <li>B) 8</li>\n        <li>C) 9</li>\n        <li>D) 10</li>\n      </ul>\n    <li>What is the product of 6 x 7?</li>\n      <ul>\n        <li>A) 36</li>\n        <li>B) 42</li>\n        <li>C) 48</li>\n        <li>D) 56</li>\n      </ul>\n    <li>What is the square root of 64?</li>\n      <ul>\n        <li>A) 6</li>\n        <li>B) 7</li>\n        <li>C) 8</li>\n        <li>D) 9</li>\n      </ul>\n    <li>What is the result of 12 / 4?</li>\n      <ul>\n        <li>A) 2</li>\n        <li>B) 3</li>\n        <li>C) 4</li>\n        <li>D) 5</li>\n      </ul>\n    <li>What is the sum of 15 + 9?</li>\n      <ul>\n        <li>A) 22</li>\n        <li>B) 23</li>\n        <li>C) 24</li>\n        <li>D) 25</li>\n      </ul>\n  </ol>\n</body>\n</html>\n```",
                        "refusal": None,
                        "annotations": [],
                    },
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 73,
                "completion_tokens": 337,
                "total_tokens": 410,
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
    # Embedding Responses
    "3923": [
        {
            "content-type": "application/json",
            "openai-model": "text-embedding-ada-002-v2",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "42",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "10000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "9999992",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_72a807dee044452d85ae14ec24d2497a",
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
            "usage": {"prompt_tokens": 8, "total_tokens": 8},
        },
    ],
    "10590": [
        {
            "content-type": "application/json",
            "openai-model": "text-embedding-ada-002-v2",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "82",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "10000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "9999998",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_39f823ffb1ba4f0db5866f82f4a16be9",
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
            "usage": {"prompt_tokens": 1, "total_tokens": 1},
        },
    ],
    "9906": [
        {
            "content-type": "application/json",
            "openai-model": "text-embedding-ada-002-v2",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "158",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "10000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "9999996",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_2f1a3eb66e7b4f55849cac5a35bcb9c9",
        },
        200,
        {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": 0,
                    "embedding": "N6UxukuzljuISqW8PMimvFQmeLufoLS6iqeAvDZENTxDzqi7AZY1vZezhDxK2Es80+23vMFEcLycXCs7TZYjPFX9oTySFkG8eVsUPNwvAT36j7O8db7QO1WDU7slcpc7a3TFvK2wWTuPUKc7ZPR0vAcWBj1J0Am9YS7bPNGImrw+MWW8TvcfvG4yHTxGkKG7LmNouQtiUbyZHMM8J1nFvJT9bjwEWK46aRfqO+2L8bpxAPm8UjcIPBNHPzpkZoG8e0JCO94SjjzRBoo8rS7JuwkB1bxcB8U81MgCvV1oQbtq7pO8/lnuPO2H0Dz4rCa8PE5YvNESbTspQPO8aQsHPO9iG7zJKd47sywJPDVAFDzh3Ei8pijHPFLB2jxSP0q8Yg1HvIBtebzg+bs8U5gEOz8Ij7xii7Y7/OwOPCk8Urx4fKg8zkiyvP+yqLuohaI8tY0FPL/fUjxJ0Im7WqrpPKEBsby8Hdq8pqKVukh78Dp9p1878wOAPG6wDLywdvM78q5mvEPKBzwVKky7qeYevQGaVrxXXh680YgavI/aebzAuh28PqszvIhS5zts1UE7bNliPBFgEbqVUoi8Ld22PG46X7yhBdK85RiQOzRdh7sVsH08JBndO2EuW7vwRai8/HLAPIuKDT35Nnk8xITYvN4aUDzjt5M7QesbvbB2c7wE1h284H9tvMC6HT1fS048EeZCPB9wtjtQ3s28ygCIPOcD3zpJ1Ko8oQExvFLF+7y6vF08pixoPPMDgDyzOGy8s66ZPG+TmTxnqoo86sl4vBADtjsYajS8aQ8oPFooWTxmTa87PNDou/z0ULkkl0w8BNo+O88nnjw8zMc7M4p+vC8+Mzd2mRu8diPuu1/R/7yj5D08MgCsPDTn2TxLMYY7Z7JMvJe/Z7zbXHi8Nb4DPLHPLb0yBM08q1N+vM7GoTsHHsi7QXFNPF/FnLzqP6a8L8TkvOugIjxVh/Q7j9bYPK4Vd7t2nbw6l79nPKS/iLu9flY8ZywbvFyFtDsf9uc8piSmPH4EOzxADDC/tZnouzbCJDy1DxY8vXaUu1OgRjzPsXA8fB2NPJkg5LupZI486N4pu4fxajzHPg+7UGBevFDeTbzT8Vi8jfPLugig2LySFsG8ZPT0O1hFTLz5sMc8LVsmvEPSSbzmeYw8KUBzujZMdzpuOl+84VYXusxlpTzi4Gm89WidPJziXDx8HQ279AtCPdYxQTwTwY27BjcaPDitczt7QsI8EAM2vL30g7xz16K59XDfvD4xZbyly+s7m4HgPL/XEDxI8R28B5iWuwl/xDyhfyC8zUSRPD+KHzyZGKI7SPW+O28RCT0Y5AI8QW0sOv5ZbjuhBdK66NqIucQG6TpsUzE8brStvAY7uzzXjpy8ed0kPE2Wo7xzWTO8PMSFu9tc+LuFCj28nGBMvI1xuzyNef08lPnNPCqVDDrjPUW8FCKKPAkFdjwsAmw7GGaTvJ+k1bwC97E8rgkUvI/W2LxzYfU6G6ocus+tTzvCpew8cXpHPGkLh7yc4ty78qIDPaCo9jsEVA280+03POrF1zymKMe72fO5O8+tT7yuDTW8gytRO6lorzzh1Ia7HY0pvJezBD0HGic9q0/dvOD5OzuISiW8mZoyvcBAzzxaJDg7ZGYBvZzm/bsdkco7PNDoPBaDhrxxAHk8gyOPO2Tw0zxzXVS8ySU9PFBk/zufGoO88wchPO1/Drzv7G28JXKXPN4SDrvHQrA83h7xu+b/vTu1F9i6BFxPPNnvGLzqvRU8C9wfuxcR+rvju7S7dcJxPJp5nrz15ow8SHvwvEaQobwnUQM7hYxNOxaLyLvoXBk8stNOvHPXIr3REu07XWziu94a0LvPsXA7wh+7vKJeDL2rU/68JXY4u5r7rjw+pxI7bxUqO9cQLbnyrua8a3hmvLhbYTyKs2O7LVsmvVWD0zzKAAi8iFJnvLWZaDqxz627XWjBO/1Ni7wBEAS8wDiNvB2NqbupaC+7xeVUu/+uh7wIpPk7Nx8APaiFojvZ7xg8E0OePEFxTbxk9HQ6pL8IPJ8eJDyKr8K88qIDOpXYObwEVA27tRdYPMA4Dbwzhl08VYPTPCIuDj1Vg1O7lPELPUFxzbxSN4i7/U0LvaEF0jvYkr28fSEuO2euqzwTwQ08v9eQvAa1CbuXOTY8+hHEPJ4/uDxiCaY798kZvHS2jrySlLC76GRbvOFWlzzREm28qI3ku9250zpnqgo9L8TkO712FD0ZSaA7INGyvBPBDb0tV4U8jXVcPIwQv7sQiWe8QfNdux2NqTzJp0281EoTPDtnKjz/tkm8E0c/PDTn2TzCH7u8RpTCO9TUZTyzOGw84dgnOZxYCrqEL/I8xV8jOyQdfropQPO6ySU9Ome2bbyDpR+9s7K6u1qq6buy1+87X0MMPbrAfjzbXPg7INXTOxWw/brzAwA8EIlnvPz48Tu2cJK88qIDvHwdjbzdvXS8w/oFvGINxzxkZoG8Nkx3O02Wo7thqKm7I4+KO/dPSzzOysI7uxm5vIwUYLwD+1I6xIRYPMkt/7o80Gi80mcGvdltCDyaeR48tY2Fu734pLwJ/TM8l7/nO8P6Bb2BQII8SHOuOzit8zxNnuW8bFdSO4sMHrwtV4U8KpWMO3AZy7y6Nqy8roeDPOUYELrJLX86l7vGuxjoo7vXDAw7+g0jPBs07ztAkmG7AvMQPI9Qpzz9TQu6kK0CO4uKDTxzXdQ8qWxQulDezbvoYDq7S7vYvFQiV7zTb0g9eIRqPF1s4rp/DH08zGWlvNtQFbyRO/a8szjsvNEKK7xJVrs7KDSQukCS4TvsKnU5BN7fO/fV/Dt2nTy7zOc1u0CSYbyeOxe7cXrHu1ogF7vJIRw8BFxPOvQPYzwEWK48OK1zO6EBMTyhCfM7urg8vBuuvbyfHqS4j9p5u0QvJTxBcU081i0gu8QG6TwiLo4866RDPYhOxjt2Fwu8Q9JJPFqeBjw8xIW7+Tb5u3u8kDsay7A5SG8NOjRlSTwayzC8q8UKvcdCsDxQXL07FoMGu8xhhLyjam+8HZHKO/KuZruN76q7j86WvIsMHr0sAuy89XDfvNESbbzeHvG7rbBZvNJrJ73NwgC9ZOgRPLFNnbwbLC28bFfSu8IbGr3OxqG8AnGAPG463zzv7G08kC8TvNGMO7wl9Cc8+TLYO6YsaLspQPO8X8UcPCdZxbvOSLI8L7iBuhuuvTz6EcS7e0bju+ho/DzZ+3s7Uj9KPOsiszy1kSa8b5OZO4opETyFkG670QorvEAMMLyDIw88Y5P4uxQiirzqwTY7mRSBO2zZYjvth1A8CQHVPLhXwDwE1p280/FYOku3Nz0zin6890uqPEhzrjoYZhO8INGyPLHLDD36i5I8roeDvJCtAr2P2vm6FCKKvNn3WjxpD6g8gOfHOv8wGLnjv1W8e8CxvBADNjv0jVK27+jMuyBX5Du6vF28UxqVufXuzryeQ1k6gG15uiOPijwf9me8faffuyBX5LyA34W8khKgOk51j7xfS069huUHvVI/Srxmz787VX8yvDelMTyAbXm8FoOGO+WiYrwCdSG6Dp6YO+FWF71ly566ARCEPI1xuzwE3l88Ii4OPTVAFDyQMzQ8uNWvO/KqxTvgf+27zkgyvNn32ry9fta8ldi5PO/kqzxTmAQ9eHiHu8KZiTsOKGs82W2IuiBLAbyKqyG7ZcueOyDRMrykRbq8szTLOvoRxDrRDkw8fZ+dOwY/3LuP2vk72e+YO0rYSzxDVNo71NDEPDEhwLvMacY872IbPBYN2brOUHS8+TLYu+wqdbtaqmk899HbO2kLhzxIc648x8hhvFyFNLuKr8I7pqrXPAGSFDzrHhI5KDSQu/QPY7uxTR08gGlYvJkUAbzRjDu8TZYjO/dHibzPK7+8cQD5OyBPIrwCcQC9scsMuyg0kLr1aB09WD2KPFogFzzcM6I89A/jO+sm1DvrnIE8TvefvFBYHLtx9BU9J1GDusXdErsxJWG8fgQ7O3s+ITuHazm7j84WvQY3mruzNMs8xV8juyx8ury6Nqw7V+jwvPDHODwOIKk7UrmYvK4Vd7y7GTk8YTL8vNiWXjz6l3W8NGGoPLjZ0DxX4C68pEU6O62wWbtutC084l7ZujtnKrwGP9w8O2eqvKS/iDw2THc8hmcYuzElYbvM7/e6BNadvAzDzTzyJJS8PMzHO4qvwrvwRag8WD0KvIJEIzyDK9G7FKSau7hb4bpNFJO8RhbTPC+4ATxBcU278q7mu4HCkryNeX28GGYTvS9CVDpvEQk87+SrvJKYUTxdZCC7E0c/PKCo9jvUzKM8lHOcu0sxhjy6Os08bNGgvIMjD7yQL5M8X8k9PGmNl7xLNac8j1Anu2xTMbucWAo8UNosvHH0lbw3qVI71MgCOwY/XDvRiBq7JXIXPDkO8DxSuZg8JXIXPJe3JbzKCMq8EInnPKeBAbse7iW8nNoauiV+erxfS048o2rvu3YXi7tzVZK7xmflvEYadLyKr0I6Stxsux5slTstVwW8UN7NvJT97rp9p9+8X81eO5AvEztYwzu8L0JUuy/AwzkyBE08brjOujzQ6DtsTxC7nNoavI/StzpNHFW8J9tVvCfTE7xSOyk9cfQVPDkCDTwvvCK8EP8UvJKQD710OJ+8bja+uWcsGzp7xNI7bxWqPP3PGzsCcYA8LmNoukaQITzHRlG8+KymvDGjUDr88C+8j9K3PMkt/7uCzvW8+S43O7wd2jsTxa4898kZOxhu1Tsaz1G83LERu/fJmbxTnKW8O+k6O6RFOjzeEo48lVKIvI9MhrvwRSg8v9uxO7WNhTvCocu8dDgfO4drubxSP8o8q81MvCI20DtcAyQ8JXa4vIqvwjxhqCm8gN+FPIBt+TyU+U08E8GNOzRdB7ovQtS7284Eu9TUZTyXPde5gyOPOnlbFDyU+U28ZOyyvIuKjbzcL4G6jBTgvG8VqrtDyoc7ll7rPG46XzwYZhO9XIlVvEHz3bxNHNU747cTPAcap7zEfBa7rbBZvCMRmztlSQ48NkS1vAect7oxHZ88X81ePI15/bqjZs48LmNoPvMDALyZGKI7X83ePDEl4Tz6EUQ8ARQlPDtnKruhCfM7ZGYBPNEOTLxYPQq8aQuHvMqCmDtQWJw7wEBPPHF2prw2TPe84H/tvH5+ibyU+c07x8CfvDpjibyQM7S87+hMPPXqrTsNx268+g0ju6Co9jx4fKi6Q1h7vLHLjLvUSpM7gsazPKailbz88C+8P4ofPdESbTzM7/c8SdAJu4blh7wYZpO8NF2Hu9cQrTueR3o7ygQpPOq9lbveEg69M4bdO/qX9TyfIsW7XeKPPIBpWDw2TPc8usB+PLHPrbyuj8U8njuXPOsiM7z8bh+8MgAsuww9HD2V2Lm76OLKPMA4jbwVKky7Z64rvY/Olrv4qIW60RJtvLWRprzXjhy7H3TXu/dPy7k1QJS8YSo6vNYxQTxGFtM7stPOPDOG3TzRiJq8TZICvD8ID7wYcva8y477vAeYFr3MZSU8NsIkvLZwErxsT5C872IbPGryNLzoXBk60RJtPCk8UjwvuAE8piQmPBsojDzOysK77+QrvOhk27uAYZY86TsFPIZnGLt5W5S8Zk0vPBjkArwfdFc88ixWO8C+vrthMvy8nbmGvBPJTzuXv+c7ZlXxvKeBATywbrG8QI5AudTMoztToEa87+jMumv2VbzF5VS8j9I3PMA4jTl52YO8yoa5u3CbWzzlomI8ez4hvXwdjTq27oE7EurjPJR3PTwf8kY7IFdkPFv/gjtangY7stdvu4WEi7sBkpQ7m4FgvENUWjzREm28vXo1vDW+A71s1cE8cQD5vHs6ALwBEAQ7TnUPvXNZMzvWs1G8/zAYvMqGOT0yfhu7KpUMvIMnsLw5DvA7TRzVupezhLwGvcs7h+3JPK6HA7ymJCa9J9/2vP1RLL4iuGA899FbPAY3mrzv7G08scuMOyBTQzwXEXo8L0JUOweYFjzyrua6J1WkvF/R/7vh1Aa92W0IvNESbbwisB68ldi5OmpwJD3ZbYg8pqY2PV9DDLwtVwU8ZGqiu3tG4zrv6Ey8tZXHO8qCGD2uFXc6a3TFvMdGUbywbrG8e7wQPUnQiTwgV+Q8vJvJuzxKNztk6BG9tu4BvPdLqjyXPdc84dQGPEHzXTyojWS8ldi5vHrl5rsOIKk840FmufzsjjxLOUi8bxUqPGXLnruPzha7hQYcOLbuAT36i5I8ujKLux2JiDxBaQu7Fgk4vIhGBLzKilq8gsazu0rYS7zo2gi8EP8UO7UXWLz/tsk7TZ5lvDcnwjyb/0+8GygMvTzIJrx7vBC9cfSVO6XLazsHmBa9CX/EPBjkgjkygjy8szhsvOhofDzPKz88/VEsPLLTzrse7iU8Rg4RvCBLATy3+uS8tnSzvBD/lDzAPK68GtPyuwn9s7wqG747J1GDPBs07zv/NLk8xAJIvHgCWrz1bL64Mn6bPKPgnLxSwVo7Dp4YPXnZg7yN76o8xVsCPCz2CD3FX6O8xVsCvBD/lDvJKd48o+CcPO1/jjyH8eo89Widu7M4bLzXDAy7yoKYu49QJz1s2WI8/64HvZ8aAzwygjy7+pd1OrOumb21mei8VfkAO1/RfzwZSSA8GccPPWcsm7tAkuE7euXmudJrJzxGDpE7eIRqvKPkvTuITsa7U5gEPRhqtLwbKIw87+SrvLLX77vKAIg8/zQ5u9GIGrxhqCk8cXKFvBCBpbzm+xw8cQB5vEs96TzHPo87rg21u6THyryAadi87X8Ou66HA7zWMcE5kC+TPM+lDb1GlEI8CKBYPATavrz9Uaw8Br1LPGIFBbzHPg+9/PAvuzOGXTxmVXE7Nx8APfoJAjwMv6y8cQB5vMC6Hb1Vg9O88MtZPB0PujtQ3k27q8WKPI113DyG5Ye7ol6MO9JnBjxwm1s7urQbva4R1jz6j7O7kC8TPKRFOrzHwJ88bjrfPKPkvTmcWIq8v9uxPFBYHLwJAdU898kZvZkYojwMuwu8hYisvOb7HDzoaHw8sHbzvIWIrLyKLTK7KpktvIwQvzxNlqM8u5OHu7/bsTvU0ES86j8mvQY3Grwe7qU8+pd1PEaMALxsT5A7+o+zPK6Hg7pnssy6wEDPPFqmyDxC9/68gyOPvAL3sb2FkO48O2vLu94Sjrwqma08EeZCO9ESbTzv7G28YocVvEW5d7vJo6y8ARjGuhYNWbxJUpo81NDEvF9LzrvhVhc9Kp3OPJ5Hersn17S6lVYpOgtaj7yoiUO8euVmO5xYCrxDygc8V9wNve7girsotiA7C2ZyvHF2JjvhVhe9ZOyyu+rJ+Dx2I+47xALIu+WaIDrvZrw81quPvD8IjzxV+QC92W2IvFqipzwiMi88jXn9uzVAlLldZCA7C2ZyOpT5zTz31Xw8XAvmO1qipzzwx7i8BkN9u9cMjLwdiYi8CKR5vGe2bbkdiYi7Pi1Evfk2+Txaoie8C1oPPYWMzbtiBQU7ygQpO/z4cbxuOt+7Pi3Eu2EuW7yLig27qI1kvPKiAzzju7Q88U3qPOB/bTp0PEC8lzm2PKRBGb3RiBo9HuoEPSX0Jzx9p9+8rhHWOmGsyjx9IS48LuHXuO2DrztYRUy7+CqWO/MHIb1nriu8vYJ3OydVpDyrxQo821CVO8Kl7LvvYps6tZGmPILKVDznA188oQlzPBaLyLskGV07A33juhHioblGEjK80RLtvKNmTjzelJ47xV8jOwvcnzwY7ES72ft7PFv/Ar0t2RW7mSDkPFBYnDuG5Qe9YKQIPffJGbxXXh48LALsPDkCjbw8xAU8ol6MumxTsTuRN1W8ARznPHFyBbx5X7U8ZGaBuruXqLvMaca8SVKaur/bsbnlomI7cBlLPKvNTLxUJng9ARAEPDGbjrt+CFw8WqppPJzamjyohaI8iEolPJR3Pbx4hOq8hmeYu2RqIjwvuIG8p4EBvRNL4LuNddy76yKzvGeqiry1E7e8j9bYPF1koDyAbXk8bNGgPEW11jvgc4q8MSVhvOB/7TvNRJE7ygCIvJTxC71K3Ow8hYzNu7uXqLxOdY+83C8BO0aMgDsjEZu7UFicu02SArx9IS48cBnLPKTDqTsWCbi88U3qvKNiLTtaIJc8EurjvIWIrLtSwdq8",
                }
            ],
            "model": "text-embedding-ada-002-v2",
            "usage": {"prompt_tokens": 4, "total_tokens": 4},
        },
    ],
    "12833": [
        {
            "content-type": "application/json",
            "openai-model": "text-embedding-ada-002-v2",
            "openai-organization": "user-rk8wq9voijy9sejrncvgi0iw",
            "openai-processing-ms": "116",
            "openai-project": "proj_0Wv6taeZjWf793P67JMswYY3",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "10000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "9999995",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_92ab81c1ce20420591176c5507d7e04e",
        },
        200,
        {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": 0,
                    "embedding": "F6KrOqe0iTyCOMA60BG9u3g/Ar2Xusg8qf+svE442bvs9ry8me6avMr56DxICTQ8ndIcvNOqm7yCB4a78E3KvO4qDz2dXPk3xft9PMGniLxK+7S7UIaUvLdPeDtJsBG8E9gSvGCXprwDOgw82gp7vO91sjup/yw5HV5Fu9FCd7q3UhC8yJRcvB54rjvn4YC8rqFdvIhnZbyiQ5M8pBurvCjnDz0zK/E7f59hPFsmMLwKJ+C8QBnIO8stuzuXiY68XRixvLVgjzzma908wI0fPDm20Lwn5He8LVgGvDp0/zqITXy8CNy8PK79F7zp04G8Ym8+u1oMx7vYG5K82z7NPHglmbnyDpG7+XEIu2Rhv7jwTcq74nCKPBGKVzzJOzo8dM4LvKyYizu8TWM8foX4O5IvaTtDJbK7c1jou36F+Lp/LNY8c7QivSQDDr0UI7Y8r9UvPaD1Vzts9XC8aIeSPHvVSLzVJvm8uBC/O48MrjzS0gO8TpQTPT6aUrwT72M8DvH4O2FV1TueA9c7nuyFvCpMnLvwM2G8anmTO8pVIzvAF3y7fuEyuyXBvLq5zm072oCePO63g7tPbCs71YIzPUMlMjx6Fxq91raFu6GCTLz8Ywk8NKGUvEOYvbtrN8K8VYFnO2JvvjyITfw7dtfdvGYihju60QU8BPi6vDp0f7z0F2M8STruuuIU0DwASIu7WKe6O2Jvvrr0AJK8n9vuPNUm+bxc5N48waeIuwyMbLx8fCY7H6wAPaU1lDvS0oO8YxacuidAMjyFRKo8y/yAvIkOw7s1X0M4z1OOPI1LZzsRitc8/JTDOw4L4jwkNMg84y65u76bHj3k7Oc7k/AvvCVOMTywYiQ89nxvPMiU3LwrCks6wacIPYoorDxUUC0795ZYPPT9ebykjra8RD+bPJhhJr37YPE7EYrXOhud/rpM08w8+ftkPJyeyrwFLA29EeaRvHhWUzxt+Ig7gjjAPEVw1TtnbSk7zQVTPPRzHbzrT9885jqjvPRznTv44fs85q0uPdMdp7p1GS+/Maz7uy6jKTwbbMS6QvHfPDRF2jtgrne6ri7SPBjT5ToLzr08hJ1MvPZ87zzYG5K7Aqr/u84fPDo8T6+7RFZsO+OhxLuSpYy8JJCCu3InLr0ARfM6qmS5u1uZOzzYjh08GlLbuhwTojzn4YC8uIPKvPZ8bzx548e8cj7/O0uIqTwt/Es8+ftkPdFFjzy1YA+8sscwPF0YsbxSeBU9DIxsOwKqf7y+Diq8lxYDvZGLIzz1jYa84uMVPNiOHbwMjGw8UJ3lu2Akmzx21128Hhz0OzGVKjw33ri7w5kJO74okzyZkuC7YK73u9xYNjye7IW4Hhx0POcSO7y8TeO7EFmdvGqqTTyg3oa8T4N8vNPBbDyIZ2U6NqpmvHKauTtc5N68KFqbu8a8RDxX6Ys83r1CvPH0J7zYASk8qRmWPD3z9Dy/tQe7SVRXvLXTGr2eA9c8ChAPvc1hDb2Y1DG7AexQO1WBZzxUw7g8rAuXPIvPCbyjAUK8j5kiPM/gArxfTAO9kOTFPFICcjtEzI+8olpkPLYePrx21108sTo8PGp5E7vBMeW7agaIvFfPIj2cK78808FsvD32jDsinoG8wACrvIT5hjx+hXg895bYvCJCxzx9lo88BPi6PLVgj7y2Hr48E9iSPKMBQjwT2BK8NqrmO0AZSDy+m568h6m2vKwLF72vSLu795bYPHWmI7xVgec7QHUCu+l3Rzw+mlI811rLPMdjIrvMXvW1z/dTuotzT7ySGBi86XdHvEu54zvKVaM85jqjvHx8JrzMRyS8VrU5u4SD47pdGLG7oPXXO07FTbw98/Q6BCn1OOKH27yPJpe7EYrXu/eW2Lv3lti83MvBO6JDEz2gxB28L72SPKYkfboALqK8unXLOunqUjzCZbe7AzqMvCMaXzwb38+8PrQ7vCZoGrxDJbI7DAKQPHDZcrwR5pG8T4N8OqzJxbzBS847kMpcOipMnDv0AJI8mQgEPXd+u7s8Ty89wwyVPMk7urxB13a6Fy+gPJhHvTwxrHu8EYpXO1LrILxS66C846HEO7c4pztGMRw8Gq4VPJ4DVzwHHg48GlJbPJPWRrxnbSk78g6RuzuoUTwqvye8wtjCPLw2kjzdjAi7olrkvP+grbvmrS67KFqbPOFWITzrq5k5H5IXO7xNY7xn+h07irWgPLszejz0ABI7PWkYvHHcCrwbnX48I1ywPNQ3ED0vMB681kDivNOqG7y2kUk8yTs6PIbRHrwn5Hc82mY1vKdYzzwGd7C7mHj3POoEPLw99oy7bGsUPO8CpzyZCAS9f/ubPKFAezwxlao8h6k2PMX+FTyZ7ho9Gq6VvOoEPDxd/ke8RYo+vBjTZTyRi6O808FsvHtI1DtQneU888w/PXx8pjwO8fi7b+qJulJeLDz+yBW8vWfMu4hn5TsnQDK6u4+0vLbtg7zttOu8huhvvN7ufDwQzKi8yCHRPNLSAzxjMAW7oN4GPKjlw7ssJLS6jyaXvC9Hb7y7M3o83Fi2PIIHhrw1kH28YK73vN8IZrppX6q8AezQu5H+rrtJIx08nVx5PHKaObyW/Bm846FEPKe0iTxC8d+7MHtBu3qKJTySGJi7GLyUuzI8iLzEV7i8JoIDPB1exbvlk8W6Mq8TvSH3ozvtnRq8SxWePKJaZDwDa8a8I1wwvDkpXLrIlFw8KXSEvG+OTzocEyI9kMpcO7gQPzyeX5G8dP9FvDkpXLwCqn89HIatO6D117tUZ348unXLug+BBT2Zew+8i+bavDaq5rpffb28I3aZvDrQuTkbbES7P86kPJ1FKDxgyGC8JvWOOtd0tLq16uu7UIaUOwbqu7z3I807PrS7O8AXfDt4sg08blp9vKK2nru/zNg7v7WHPItClbxJOu467wInPO4qDzsCxOi7VrU5PAon4Dz8Y4k6oMSdPIccwroWV4i82gp7PFRQrTw5tlC8ChCPvPH0JzwYSYm8smt2vKjlQzz7SaC8iiisuueFRjzBS068BIWvvGItbbwhEY28Wn9SPH+f4btOOFm8PE+vvN1yn7zWKZG8Rrv4vHd+uzsO8Xi7mjm+vAjcPL3cifC8rxeBvF/wyLyBehE8Qaa8vPWNhrxxgNC81YKzOzgP8zyrImg8hgLZu43Birx5cDy7ZiKGu1TdITy3OCe8+VcfPHbADDvcifC7N944PNErJjzYjh28AEVzvE442TwAu5Y8UgJyPD6aUjw2k5W8v7UHvKJDkzyiQ5O7jmVQvIndiLx0jDq7bGuUuzYgirxvXRW8/HravFoMRzwYvJQ7rv2Xu9yJ8DyTYzu8Hx+MvLdp4TxNBx+8yy07PFfpC7xJIx083YyIPEJNmjwIqwI9VuZzu9m/17yb9+y669zTvFCGlDy4g8o8yuIXvD6DgTyhD0E8ZQiduwmDGrrBMWW8H6yAvN4wzjsXoiu8FleIvM6ssLysmAu81kBivOCvwzy9gTW8QtqOuzrqorxCTRo8b+oJvPtJoLw4D/O8RLImvcAX/LtKbsA805CyPF/wyDuFRCq8foX4usN/ILxx89s7RXDVO66h3bzZqIY78g6RPCZomjzhbXI8k2O7PNs+Tbre7nw8fO8xvBo7CjyOfzm8blp9vDt3l7w9DV68gjjAPPHavjx1Ga88xD1PPCH3IzhC2g48b12VuQmDmjtTHNu7MxQgvNYpEbyG0R65RVkEPIUqQbw+tDu7eLINPP0hOLzEVzg7qkpQOzw1RjyduDO8XqUlPRK+Kbxbmbs7BBIkO1RnfrucK7+8LCQ0vAmDmjyPJhc84hTQPEe+kDxQnWU8e2I9vFll6buGAlm8VubzPKXZ2To2qua7fm6nuwEGOrzL/AC8AC4ivI3BiryGAlm8OSncO69IO7zL/AC8CWmxPNok5Ly3aeG8MjwIvN9koLxeMho94nCKO3Hz2zwT2JI86zgOPJQKGbuv1S88BUPeuncLMLzeSrc84CJPPLRGJrrBMWW8R9VhPK8XATwkA4687RCmvBcvoLsw7sw86pGwO5yeyrs2IIo8SbCRvErhyzzVD6g7qwj/u/8TObyXLdS71MSEvO2dGjxyPn+8cieuO9oK+zwlTjE85+EAvHNY6DpzQRe7M/o2u3HzW7xzWOg87s7UvAVD3jsz+rY7cdyKPJ8dwLyT8C88L0fvO19MgzwZekO8IkLHvD6DAbyy4Zm4V1wXPNLpVDzHYyI8rqHdvLNuDrvhbfK75AbRPEWKvrtbynW7msayvOOhRLvMXvW8ZXsovYjDH7yG0R4805Cyu/AzYb3BMWW83whmPEJng7sHkZk8ZaziuymlvjuQs4s8G9/PuwwCkLpfTAO8RD+bPKYNrLxEVmy7BZ+Yu7AGarwgUMY77Pa8uxjT5byINis7O45oPHzvsTwn5Hc73f+TO+KHWzyGXpM8U6nPu1k0rzs17Le8qRkWPRSWwbsuoyk8VkKuu7DvGLtFWYQ7ym+MvGwP2rv7SSA8eFbTvHzvsTvi45U7/sgVO/NZNDtSAvK6SuHLvFk0L7xAdYK8V1yXPEYXsztmxsu8v8xYPC8wnjtnbak8irUgPN/XqzpeY9S8/a6svOMuObqIZ+W8auwePEQ/Gzy8TeM8ge0cO1JeLLuxOry8mR9Vu+4qD72UlHW7JDRIuz32jLrQhEg81YIzPIPfHTtIlig9FCO2um7QoDzK+ei8Y9TKOz9y6jx2wIy8rqHdOx0tC7wpGMq8vrJvvKqmijyekEu8lSQCve0QpjxGpCc8aV8qu0sVnrxpXyq82b/XuoSdTDz0F2M8XqUlvNErprzvAie7iQ5DvKqmijvhViG7/Tshu25afbyZ7po8mjk+vEB1ArzP4II83InwvMiUXDwwSoc7dmRSvIW3tTwY02W89THMO4Nperxjo5A8t2nhvLXTmjwchq04GNNlvJl7j7xq7B68MjyIvNgBqbw/Wxm7rAsXvac+Zrkuo6m8lJT1PHglmTsVsKq8Mm1CvB4c9LtX6Qu8UUTDPGV7qLwXLyA5AF/cvI+wczwHqOo8Z/qdvHqkjrxTNkQ8tepru48mFzwjGt88WWVpPrjfhLzVJnk6JJACPUufejyf22689ks1Pbp1y7tEsia7Y6OQPM6ssLzj0n68BIWvvDaTFTx9lo88STpuu6PQB70Rcwa84nAKvUVZBL2xrUe7Ul6su7pEkbvUxIS8uSqoPJo5vjqY1DE5ef0wPIvPiTyrImg7XknrvBcVt7yMjbg8n9vuPN7ufDrL/AA8vfTAPDBKBzwQcG48XklrPD6DgTvLoEY8yPAWvNacnLz3llg8cdyKPK8XATxoK1i8dRkvPGIt7TwFQ168Svu0O4ndCD3Kbww9vfRAvEB1gjze7ny7jn+5uk+DfLueA9c6uBC/u7fFGz3uzlQ87reDPOAiT7wQPzQ8GTjyvKhyODrFFWc8rqHdOvd/B7s/ziQ8New3O9/XK7xwNS29SVRXvCvZkDxgJBs8rAsXPTShFD0S1fq7mQiEOoepNjy5Kqi80IRIvLDvGL0j6SQ8p5qgPApBybxGFzO7nXbiO0k9BrzGvEQ8GiEhPFinujyW4jA8m1MnPLF8jTzPU468DHUbOz3z9LwvvRK8/TshvMxedTut466846FEu1fPorsnQLI83u58O0CM07yxrUe8eqF2vKN0TTzRuBq8TGDBO9CEyLulwgg8R0sFO32Wj7r3I007wthCuxwTIjzDsFq7iGflPFFEwzv/E7m8BUPeulHRN7xTHFs795bYvCMAdjyBehE76NDpPJrGsrt2ZFI7i+ZaPGKJJ7v+3+Y83aPZvEAZyDskA448t2lhvDkSC7w/Wxk8YzCFvAeRGb32S7U7Bx6OvOtP37woi1W8UBMJvXUzmLxepaW5bfgIu48mlzxOOFk7ze4BvRl6w7vrqxk5WU6YPBZXCLz71pQ7JmgaPMnff7z7vKu8sO+YvIFgKL6XiQ49Kr+nu6IpqrzI8JY8qmQ5PCjNpjw0RVo8YeLJvAM6jLoVPZ88s4XfvIq1oLwDa8a8s24OvPT9ebzzzD+84H4JPB4cdD35cQg8TiGIPKdYz7xs9XA82KVuvOtPXzuzhV+8dHJRO/xjCT24EL+8yJRcO0r7tLzp6tI7hINjOv3F/Tt1Ga+7ezGDu/iwQTurfqK8BdBSvEk9hjzTHac8ZGE/PKD11zsCIKO8jUvnuVWB57tx81s87MWCPKIpKj0kA46711rLPKc+5rzhPDg8BIWvPAqdA7udXHk8OGstvH8VhTzTwWy8eXA8PLw2EjxAdYK8/4bEPPyUw7s00s66AF/cOtokZDv9OyE8cDUtvEOYPTydXPm7hGwSvbnObTurIui808FsPA1NMzw/ziS9OIWWPG8bxLx/FQW8wUvOu4T5hjqMjbi8XqUlvMdjoryocjg8hujvO5GLozukqB+8r9WvvL9ZzTwPJUu83Fi2vA0zyrtsD9o7ylUjPH3HyTvGiwo6CQ33u0J+1DvaCvs7fyxWvLdPeDwRcwY8RXBVPKVmzjuaxjI8kf6uPKN0zbtZZek63aNZvO5byTyyVKU8utEFPQLE6LvI8BY8XklrvMnff7z1jYY87MWCO7+1Bz2Lzwm6L70SvXn9MLvbDZO7BPg6u+cSu73aZjW8mGEmO57shTsLWzI8ALsWPeB+CbsdXsU8T2wrPAjcvDsNwL68UBMJvHqkjrxmIga8RMyPPJSXjbzF+308iE38vNlMzLznhcY8ZJJ5vDV5rLwCky47xMrDvEfvyrskkII7LT6dvMdjIjwW+808R76QOYhNfLyKKCy8QyUyPMmuRbzfZKC7h6k2uJ3SHL0frIA8vpsePHRbAL38B088z/fTu2z1cDsVVPC8id0IPAx1mzvon6+8EXMGPJBAgLwKQcm6ST0GvQUsjbzK+ei81DeQO4W3tTxOONm6ZJL5O+MuuTtrUau7bN4fvLbtA7p548e72ma1vGTuszxLn3q7Qk2aO+Y6o7wJDfc7ZQidO5IvabtLohK8kXE6PW/qCTwDa0Y8ervfvCq/p7t2ZNK89BfjvKSONjyg9Ve74cksvEYxnLylwoi7gQTuu5hHPbuE+YY8hgJZuxcvIDuocri7SuHLvM3uATy+m548VYHnuhudfjwwCLY7pcKIN0B1gryXLVS78g4RPbJUpTtmxku8ZiIGvC3iYr3CZbc8QTOxvCYmybzih1s7f59hvERWbLsS1Xq7o9CHvAjcvLuaxrI7CfYlvFLroDvDmYk7uSoovd69QjwQPzQ9HnguPLp1SzysPFE8yd9/vOTsZ7wVyhM8wHO2PIhn5TuYR706z93qvDxPrzyNS2c7n9vuvAT4ujz+3+a8NgYhPC9h2Dxw2XK87ioPPDzCOjvwjxs9/lWKvMiU3LmlNZS8kLOLvF6/jjyfqrS5m/dsvOnq0rgAX1y45NUWOxcvID1UUK07oN4GvI00ljwD3lG8YAqyu4vPiTpCTZq8MO5MvLsz+juARr861DcQvef4UT0wSgc89OaoPHNBFzwO2qc7B5GZO+z2PLxohxK8lVW8uw+BBb3IfYu8Is+7u3ZkUryBepE7dsCMPAPHgDxwwiE7YoknO4vPCb0YSYk8TGDBPIFgqDzK+Wi8iFCUPNacHD0S1Xo8QOgNu3I+f7uUrt66uwJAPMd687xV9wq7i3NPvEuiEj3F+/25iQ7DuypjbTt87zE5AEiLPKDehjytcCM49TFMOSV/a7wvMJ68I+kkvPWNBryJ3Yi8zWENvW8bRDwqTBw90UUPPDOHqzuiWuQ8ObZQO6mMobx6oXa769xTPJkfVbyG0R69i88JPbc4pzqekMs87rcDPd7u/Lxiiac87bTrO+IUUDkKEA+8QvHfO/x6WrylZs67kqWMPOTVlrySL2m8XjIavOFt8roizzu8EHDuPHbADDvNeF49DAKQOtTb1bvwj5s8IxpfPPu8qzxLn/o8WgxHOnq737xPg/y7H5KXPPIOETxk7jO8fCDsvD1pmLzFcSG7m22QvNsNk7kR5pG7tEamPDQuiTzzzL87kYujPA70kLvdjIi8XRgxu/ZLNTwMjGw87IOxu1J4Fb25nbM8AsTou9Lp1Lx5cDy52KVuPB+SF7toFIe84H6JOzYgCjy0Ria7lJT1up124rzwj5u854VGvVM2RDv5cYg8H5IXvNZAYjzf8ZS7",
                }
            ],
            "model": "text-embedding-ada-002-v2",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
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
            if prompt == k:
                headers, status_code, response = v
                break
        else:  # If no matches found
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Unknown Prompt ({'Streaming' if stream else 'Non-Streaming'}):\n{prompt}".encode())
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
