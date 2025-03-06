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

STREAMED_RESPONSES = {
    "Stream parsing error.": [
        {
            "Content-Type": "text/event-stream",
            "openai-model": "gpt-3.5-turbo-0613",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "516",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-remaining-requests": "199",
            "x-ratelimit-remaining-tokens": "39940",
            "x-ratelimit-reset-requests": "7m12s",
            "x-ratelimit-reset-tokens": "90ms",
            "x-request-id": "49dbbffbd3c3f4612aa48def69059ccd",
        },
        200,
        [
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [
                    {"index": 0, "delta": {"role": "assistant", "content": ""}, "logprobs": None, "finish_reason": None}
                ],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": "212"}, "logprobs": None, "finish_reason": None}],
            },
        ],
    ],
    "Invalid API key.": [
        {"Content-Type": "application/json; charset=utf-8", "x-request-id": "4f8f61a7d0401e42a6760ea2ca2049f6"},
        401,
        {
            "error": {
                "message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_api_key",
            }
        },
    ],
    "Model does not exist.": [
        {"Content-Type": "application/json; charset=utf-8", "x-request-id": "cfdf51fb795362ae578c12a21796262c"},
        404,
        {
            "error": {
                "message": "The model `does-not-exist` does not exist",
                "type": "invalid_request_error",
                "param": None,
                "code": "model_not_found",
            }
        },
    ],
    "You are a scientist.": [
        {
            "Content-Type": "text/event-stream",
            "openai-model": "gpt-3.5-turbo-0613",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "516",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-remaining-requests": "199",
            "x-ratelimit-remaining-tokens": "39940",
            "x-ratelimit-reset-requests": "7m12s",
            "x-ratelimit-reset-tokens": "90ms",
            "x-request-id": "49dbbffbd3c3f4612aa48def69059ccd",
        },
        200,
        [
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [
                    {"index": 0, "delta": {"role": "assistant", "content": ""}, "logprobs": None, "finish_reason": None}
                ],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": "212"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " degrees"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " Fahrenheit"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " is"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " equal"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " to"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " "}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": "100"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " degrees"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " Celsius"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": "."}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
                "object": "chat.completion.chunk",
                "created": 1706565311,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {}, "logprobs": None, "finish_reason": "stop"}],
            },
        ],
    ],
}

RESPONSES_V1 = {
    "Model does not exist.": [
        {"content-type": "application/json; charset=utf-8", "x-request-id": "req_715be6580ab5bf4eef8d2b0893926ec9"},
        404,
        {
            "error": {
                "message": "The model `does-not-exist` does not exist or you do not have access to it.",
                "type": "invalid_request_error",
                "param": None,
                "code": "model_not_found",
            }
        },
    ],
    "Invalid API key.": [
        {"content-type": "application/json; charset=utf-8", "x-request-id": "req_7ffd0e41c0d751be15275b1df6b2644c"},
        401,
        {
            "error": {
                "message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_api_key",
            }
        },
    ],
    "You are a scientist.": [
        {
            "content-type": "application/json",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "1676",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "60000",
            "x-ratelimit-remaining-requests": "9993",
            "x-ratelimit-remaining-tokens": "59880",
            "x-ratelimit-reset-requests": "54.889s",
            "x-ratelimit-reset-tokens": "120ms",
            "x-request-id": "req_25be7e064e0c590cd65709c85385c796",
        },
        200,
        {
            "id": "chatcmpl-9NPYxI4Zk5ztxNwW5osYdpevgoiBQ",
            "object": "chat.completion",
            "created": 1715366835,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "212 degrees Fahrenheit is equivalent to 100 degrees Celsius. \n\nThe formula to convert Fahrenheit to Celsius is: \n\n\\[Celsius = (Fahrenheit - 32) \\times \\frac{5}{9}\\]\n\nSo, for 212 degrees Fahrenheit:\n\n\\[Celsius = (212 - 32) \\times \\frac{5}{9} = 100\\]",
                    },
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 26, "completion_tokens": 75, "total_tokens": 101},
            "system_fingerprint": None,
        },
    ],
    "No usage data": [
        {
            "content-type": "application/json",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "324",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "60000",
            "x-ratelimit-remaining-requests": "9986",
            "x-ratelimit-remaining-tokens": "59895",
            "x-ratelimit-reset-requests": "1m55.869s",
            "x-ratelimit-reset-tokens": "105ms",
            "x-request-id": "req_2c8bb96fe67d2ccfa8305923f04759a2",
        },
        200,
        {
            "id": "chatcmpl-9NPZEmq5Loals5BA3Uw2GsSLhmlNH",
            "object": "chat.completion",
            "created": 1715366852,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello! How can I assist you today?"},
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 9, "total_tokens": 19},
            "system_fingerprint": None,
        },
    ],
    "This is an embedding test.": [
        {
            "content-type": "application/json",
            "openai-model": "text-embedding-ada-002",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "17",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "3000",
            "x-ratelimit-limit-tokens": "1000000",
            "x-ratelimit-remaining-requests": "2999",
            "x-ratelimit-remaining-tokens": "999994",
            "x-ratelimit-reset-requests": "20ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_eb2b9f2d23a671ad0d69545044437d68",
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
            "usage": {"prompt_tokens": 6, "total_tokens": 6},
        },
    ],
}

STREAMED_RESPONSES_V1 = {
    "Invalid API key.": [
        {"content-type": "application/json; charset=utf-8", "x-request-id": "req_a78a2cb09e3c7f224e78bfbf0841e38a"},
        401,
        {
            "error": {
                "message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_api_key",
            }
        },
    ],
    "Model does not exist.": [
        {"content-type": "application/json; charset=utf-8", "x-request-id": "req_a03714410fba92532c7de2532d8cf46c"},
        404,
        {
            "error": {
                "message": "The model `does-not-exist` does not exist",
                "type": "invalid_request_error",
                "param": None,
                "code": "model_not_found",
            }
        },
    ],
    "You are a scientist.": [
        {
            "content-type": "text/event-stream",
            "openai-model": "gpt-3.5-turbo-0613",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "6326",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-remaining-requests": "198",
            "x-ratelimit-remaining-tokens": "39880",
            "x-ratelimit-reset-requests": "11m32.334s",
            "x-ratelimit-reset-tokens": "180ms",
            "x-request-id": "f8d0f53b6881c5c0a3698e55f8f410ac",
        },
        200,
        [
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [
                    {"index": 0, "delta": {"role": "assistant", "content": ""}, "logprobs": None, "finish_reason": None}
                ],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": "212"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " degrees"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " Fahrenheit"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " is"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " equal"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " to"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " "}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": "100"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " degrees"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": " Celsius"}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {"content": "."}, "logprobs": None, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
                "object": "chat.completion.chunk",
                "created": 1707867026,
                "model": "gpt-3.5-turbo-0613",
                "system_fingerprint": None,
                "choices": [{"index": 0, "delta": {}, "logprobs": None, "finish_reason": "stop"}],
            },
        ],
    ],
}
RESPONSES = {
    "Invalid API key.": (
        {"Content-Type": "application/json; charset=utf-8", "x-request-id": "4f8f61a7d0401e42a6760ea2ca2049f6"},
        401,
        {
            "error": {
                "message": "Incorrect API key provided: invalid. You can find your API key at https://platform.openai.com/account/api-keys.",
                "type": "invalid_request_error",
                "param": "null",
                "code": "invalid_api_key",
            }
        },
    ),
    "Embedded: Invalid API key.": (
        {"Content-Type": "application/json; charset=utf-8", "x-request-id": "4f8f61a7d0401e42a6760ea2ca2049f6"},
        401,
        {
            "error": {
                "message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
                "type": "invalid_request_error",
                "param": "null",
                "code": "invalid_api_key",
            }
        },
    ),
    "Model does not exist.": (
        {"Content-Type": "application/json", "x-request-id": "cfdf51fb795362ae578c12a21796262c"},
        404,
        {
            "error": {
                "message": "The model `does-not-exist` does not exist",
                "type": "invalid_request_error",
                "param": "null",
                "code": "model_not_found",
            }
        },
    ),
    "No usage data": [
        {
            "content-type": "application/json",
            "openai-model": "gpt-3.5-turbo-0613",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "6326",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-limit-tokens_usage_based": "40000",
            "x-ratelimit-remaining-requests": "198",
            "x-ratelimit-remaining-tokens": "39880",
            "x-ratelimit-remaining-tokens_usage_based": "39880",
            "x-ratelimit-reset-requests": "11m32.334s",
            "x-ratelimit-reset-tokens": "180ms",
            "x-ratelimit-reset-tokens_usage_based": "180ms",
            "x-request-id": "f8d0f53b6881c5c0a3698e55f8f410ac",
        },
        200,
        {
            "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug",
            "object": "chat.completion",
            "created": 1701995833,
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "212 degrees Fahrenheit is equal to 100 degrees Celsius.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": None,
            "system_fingerprint": None,
        },
    ],
    "This is an embedding test.": (
        {
            "Content-Type": "application/json",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "54",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "150000",
            "x-ratelimit-remaining-requests": "197",
            "x-ratelimit-remaining-tokens": "149994",
            "x-ratelimit-reset-requests": "19m45.394s",
            "x-ratelimit-reset-tokens": "2ms",
            "x-request-id": "c70828b2293314366a76a2b1dcb20688",
        },
        200,
        {
            "data": [
                {
                    "embedding": "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",
                    "index": 0,
                    "object": "embedding",
                }
            ],
            "model": "text-embedding-ada-002-v2",
            "object": "list",
            "usage": {"prompt_tokens": 6, "total_tokens": 6},
        },
    ),
    "You are a scientist.": (
        {
            "Content-Type": "application/json",
            "openai-model": "gpt-3.5-turbo-0613",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "1469",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-remaining-requests": "199",
            "x-ratelimit-remaining-tokens": "39940",
            "x-ratelimit-reset-requests": "7m12s",
            "x-ratelimit-reset-tokens": "90ms",
            "x-request-id": "49dbbffbd3c3f4612aa48def69059ccd",
        },
        200,
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "message": {
                        "content": "212 degrees Fahrenheit is equal to 100 degrees Celsius.",
                        "role": "assistant",
                    },
                }
            ],
            "created": 1696888863,
            "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTemv",
            "model": "gpt-3.5-turbo-0613",
            "object": "chat.completion",
            "usage": {"completion_tokens": 11, "prompt_tokens": 53, "total_tokens": 64},
        },
    ),
    "You are a mathematician.": (
        {
            "Content-Type": "application/json",
            "openai-model": "gpt-3.5-turbo-0613",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "1469",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-remaining-requests": "199",
            "x-ratelimit-remaining-tokens": "39940",
            "x-ratelimit-reset-requests": "7m12s",
            "x-ratelimit-reset-tokens": "90ms",
            "x-request-id": "49dbbffbd3c3f4612aa48def69059aad",
        },
        200,
        {
            "choices": [
                {"finish_reason": "stop", "index": 0, "message": {"content": "1 plus 2 is 3.", "role": "assistant"}}
            ],
            "created": 1696888865,
            "id": "chatcmpl-87sb95K4EF2nuJRcTs43Tm9ntTeat",
            "model": "gpt-3.5-turbo-0613",
            "object": "chat.completion",
            "usage": {"completion_tokens": 11, "prompt_tokens": 53, "total_tokens": 64},
        },
    ),
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

        if openai_version < (1, 0):
            mocked_responses = RESPONSES
            if stream:
                mocked_responses = STREAMED_RESPONSES
        else:
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
        if openai_version < (1, 0):
            prompt = content.get("prompt", None) or content.get("input", None) or content.get("messages")[0]["content"]
        else:
            prompt = content.get("input", None) or content.get("messages")[0]["content"]
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
