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
                "message": "The model `does-not-exist` does not exist or you do not have access to it.",
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
        {
            "content-type": "application/json; charset=utf-8",
            "x-request-id": "req_444007a576dc4971a009b0de4967fb60"
        },
        401,
        {
            "error": {
                "message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_api_key"
            }
        }
    ],
    "You are a scientist.": [
        {
            "content-type": "application/json",
            "openai-organization": "nr-test-org",
            "openai-processing-ms": "978",
            "openai-project": "proj_id",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "15000",
            "x-ratelimit-limit-tokens": "40000000",
            "x-ratelimit-remaining-requests": "14999",
            "x-ratelimit-remaining-tokens": "39999979",
            "x-ratelimit-reset-requests": "4ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_983c5abb07aa4f51b858f855fc614d08"
        },
        200,
        {
            "id": "chatcmpl-CoLlpfFdbk9D0AbjizzpQ8hMwX9AY",
            "object": "chat.completion",
            "created": 1766116121,
            "model": "gpt-5.1-2025-11-13",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "212\u00b0F is 100\u00b0C.",
                        "refusal": None,
                        "annotations": []
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 25,
                "completion_tokens": 16,
                "total_tokens": 41,
                "prompt_tokens_details": {
                    "cached_tokens": 0,
                    "audio_tokens": 0
                },
                "completion_tokens_details": {
                    "reasoning_tokens": 0,
                    "audio_tokens": 0,
                    "accepted_prediction_tokens": 0,
                    "rejected_prediction_tokens": 0
                }
            },
            "service_tier": "default",
            "system_fingerprint": None
        }
    ],
    "No usage data": [
        {
            "content-type": "application/json",
            "openai-organization": "nr-test-org",
            "openai-processing-ms": "2108",
            "openai-project": "proj_id",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "15000",
            "x-ratelimit-limit-tokens": "40000000",
            "x-ratelimit-remaining-requests": "14999",
            "x-ratelimit-remaining-tokens": "39999994",
            "x-ratelimit-reset-requests": "4ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_ed0c7fcff6954a85ab0956c448163b9f"
        },
        200,
        {
            "id": "chatcmpl-CobAB9gf7iGzucSqbtQZCUKWQolUq",
            "object": "chat.completion",
            "created": 1766175291,
            "model": "gpt-5.1-2025-11-13",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "refusal": None,
                        "annotations": []
                    },
                    "finish_reason": "length"
                }
            ],
            "usage": {
                "prompt_tokens": 9,
                "completion_tokens": 100,
                "total_tokens": 109,
                "prompt_tokens_details": {
                    "cached_tokens": 0,
                    "audio_tokens": 0
                },
                "completion_tokens_details": {
                    "reasoning_tokens": 100,
                    "audio_tokens": 0,
                    "accepted_prediction_tokens": 0,
                    "rejected_prediction_tokens": 0
                }
            },
            "service_tier": "default",
            "system_fingerprint": None
        }
    ],
    "This is an embedding test.": [
        {
            "content-type": "application/json",
            "openai-model": "text-embedding-3-small",
            "openai-organization": "nr-test-org",
            "openai-processing-ms": "147",
            "openai-project": "proj_id",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "10000",
            "x-ratelimit-limit-tokens": "10000000",
            "x-ratelimit-remaining-requests": "9999",
            "x-ratelimit-remaining-tokens": "9999994",
            "x-ratelimit-reset-requests": "6ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_215501af84244a0891dc2c7828e36c28"
        },
        200,
        {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": 0,
                    "embedding": "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"
                }
            ],
            "model": "text-embedding-3-small",
            "usage": {
                "prompt_tokens": 6,
                "total_tokens": 6
            }
        }
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
                "message": "The model `does-not-exist` does not exist or you do not have access to it.",
                "type": "invalid_request_error",
                "param": None,
                "code": "model_not_found",
            }
        },
    ],
    "You are a scientist.": [
        {
            "content-type": "text/event-stream; charset=utf-8",
            "openai-organization": "nr-test-org",
            "openai-processing-ms": "386",
            "openai-project": "proj_id",
            "openai-version": "2020-10-01",
            "x-ratelimit-limit-requests": "15000",
            "x-ratelimit-limit-tokens": "40000",
            "x-ratelimit-remaining-requests": "14999",
            "x-ratelimit-remaining-tokens": "39999978",
            "x-ratelimit-reset-requests": "4ms",
            "x-ratelimit-reset-tokens": "0s",
            "x-request-id": "req_f821c73df45f4e30821a81a2d751fe64"
        },
        200,
        [
            {
                "id": "chatcmpl-CocmvmDih6DGKIgPUbrzKFxGnMyco",
                "object": "chat.completion.chunk",
                "created": 1766181537,
                "model": "gpt-5.1-2025-11-13",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": "",
                            "refusal": None
                        },
                        "finish_reason": None
                    }
                ],
                "obfuscation": "7AdzF"
            },
            {
                "id": "chatcmpl-CocmvmDih6DGKIgPUbrzKFxGnMyco",
                "object": "chat.completion.chunk",
                "created": 1766181537,
                "model": "gpt-5.1-2025-11-13",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": "212"
                        },
                        "finish_reason": None
                    }
                ],
                "obfuscation": "4FR1"
            },
            {
                "id": "chatcmpl-CocmvmDih6DGKIgPUbrzKFxGnMyco",
                "object": "chat.completion.chunk",
                "created": 1766181537,
                "model": "gpt-5.1-2025-11-13",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": "\u00b0F"
                        },
                        "finish_reason": None
                    }
                ],
                "obfuscation": "BIIOg"
            },
            {
                "id": "chatcmpl-CocmvmDih6DGKIgPUbrzKFxGnMyco",
                "object": "chat.completion.chunk",
                "created": 1766181537,
                "model": "gpt-5.1-2025-11-13",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": " is"
                        },
                        "finish_reason": None
                    }
                ],
                "obfuscation": "lp2C"
            },
            {
                "id": "chatcmpl-CocmvmDih6DGKIgPUbrzKFxGnMyco",
                "object": "chat.completion.chunk",
                "created": 1766181537,
                "model": "gpt-5.1-2025-11-13",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": " "
                        },
                        "finish_reason": None
                    }
                ],
                "obfuscation": "UCIK6d"
            },
            {
                "id": "chatcmpl-CocmvmDih6DGKIgPUbrzKFxGnMyco",
                "object": "chat.completion.chunk",
                "created": 1766181537,
                "model": "gpt-5.1-2025-11-13",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": "100"
                        },
                        "finish_reason": None
                    }
                ],
                "obfuscation": "VIpm"
            },
            {
                "id": "chatcmpl-CocmvmDih6DGKIgPUbrzKFxGnMyco",
                "object": "chat.completion.chunk",
                "created": 1766181537,
                "model": "gpt-5.1-2025-11-13",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": "\u00b0C"
                        },
                        "finish_reason": None
                    }
                ],
                "obfuscation": "uHzcW"
            },
            {
                "id": "chatcmpl-CocmvmDih6DGKIgPUbrzKFxGnMyco",
                "object": "chat.completion.chunk",
                "created": 1766181537,
                "model": "gpt-5.1-2025-11-13",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": "."
                        },
                        "finish_reason": None
                    }
                ],
                "obfuscation": "WDub1R"
            },
            {
                "id": "chatcmpl-CocmvmDih6DGKIgPUbrzKFxGnMyco",
                "object": "chat.completion.chunk",
                "created": 1766181537,
                "model": "gpt-5.1-2025-11-13",
                "service_tier": "default",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ],
                "obfuscation": "2"
            }
        ]
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
                    "embedding": "SLewvFF6iztXKj07UOCQO41IorspWOk79KHuu12FrbwjqLe8FCTnvBKqj7sz6bM8qqUEvFSfITpPrJu7uOSbPM8agzyYYqM7YJl/PBF2mryNN967uRiRO9lGcbszcuq7RZIavAnnNLwWA5s8mnb1vG+UGTyqpYS846PGO2M1X7wIxAO8HfgFvc8s8LuQXPQ5qgsKPOinEL15ndY8/MrOu1LRMTxCbQS7PEYJOyMx7rwDJj+79dVjO5P4UzmoPZq8jUgivL36UjzA/Lc8Jt6Ru4bKAL1jRiM70i5VO4neUjwneAy7mlNEPBVpoDuayo28TO2KvAmBrzzwvyy8B3/KO0ZgCry3sKa6QTmPO0a1Szz46Iw87AAcPF0O5DyJVZw8Ac+Yu1y3Pbqzesw8DUDAuq8hQbyALLy7TngmPL6lETxXxLc6TzXSvKJrYLy309c8OHa0OU3NZ7vru2K8mIXUPCxrErxLU5C5s/EVPI+wjLp7BcE74TvcO+2aFrx4A9w80j+Zu/aAojwmzU08k/hTvBpL4rvHFFQ76YftutrxL7wyxgK9BsIevLkYkTq4B028OZnlPPkcgjxhzfS79oCiuB34BbwITTq97nrzOugwRzwGS1U7CqTgvFxROLx4aWG7E/DxPA3J9jwd+AU8dVWPvGlc2jzwWae57nrzu569E72GU7e8Vn9+vFLA7TtVbZE8eOCqPG+3Sjxr5/W8s+DRPE+sm7wFKKQ8A8A5vUSBVryeIxk8hsqAPAeQjryeIxm8gU/tuxVpoDxVXM250GDlOlEDwjs0t6O8Tt6rOVrGHLvmyFy6dhI7PLPxlbv3YP88B/YTPEZgCrxqKsq8Xh+ou96wQLp5rpo8LSg+vL63/rsFjqk8E/DxPEi3MDzTcw66PjcqPNgSfLwqnaK85QuxPI7iHL2+pRE8Z+ICOxzEELvph+07jHqyu2ltnrwNQMC82BL8vAOdiDwSqo88CLM/PCKFBrzmP6a85Nc7PBaM0bvh1VY7NB2pvMkF9Tx3New87mgGPAoKZjo+nS+/Rk/GucqwMz3fwYS8yrCzPMo56jyDHV08XLe9vB4+aLwXwMY8dVUPvCFATbx2eMC8V7NzvEnrpTsIxIO7yVmNu2lc2ryGQnM8A6/1PH/VFbySO6g80i5VPOY/prv6cyi7W5QMPJVP+jsyLIi84H6wPKM50DrZNIS8UEaWPPrIaTzvrmg8rcoaPRuQm7ysH9y8OxIUO7ss4zq3Od08paG6vAPAuTjYAI88/qmCuuROhbzBMK08R4M7u67+j7uClKa6/KedOsqNArzysM08QJ8UvMD8t7v5P7M799fIvAWx2jxiEi48ja6nPL0LFzxFkpq7LAWNPA1AQLyWlLO6qrfxvOGypTxJUau8aJ8uPceLnTtS0TG9omtgPO7xPDvzbfm7FfJWu2CqwzwAASk96FN4PLPgUbwRdhq8Vn9+PLk7wjs8NUW84yx9vHJCZjzysM079hodO/NbDL2BxrY6CE26OzpEpDv7DaM8y0quO41IIr1+Kte8QdMJvKlxDzy9+lI8hfyQPA3J9jzWmKS7z6O5u4a5vLtXKj088XzYO1fEtzwY4/e7Js1NugbCnjymxOu7906SvPSPAb1ieDO8dnjAu/EW0zp/b5C8mGIjvWTPWTwIxIM8YgFqPKvrZrwKpOA7/jK5O2vViDyfaXs8DR2Pu0AFGrvTc446IIOhvDreHrxRnTw8ROdbu55Gyrsht5Y8tVmAvHK5rzzZvTo8bx1QPMglmLvigBU8oIuDvAFYz7pblIw8OZnlOsTvPbxhzfS8BxnFOpkwE72E60w7cNp7utp6ZrtvHdC4uwmyO5dRX7sAm6M7kqEtvElRK7yWg++7JHanvM6ACDvrZqG8Xh+oupQsyTwkZWO8VzuBu5xVKbzEZoc7wB9pvA796zyZlpi8YbsHvQs+W7u9cZy8gKMFOxYDGzyu7Uu71KeDPJxVqbxwyI68VpDCu9VT67xKqFG7KWmtuvNteTocs0w7aJ8uPMUSbzz6cyg8MiwIPEtlfTo+wOA75tkgu7VZgDw8WPa8mGIjPKq38bsr0Zc7Ot4evNNiyju9C5c7YCENPP6pAj3uV8I7X3bOusfxIjvpZLy655bMvL9ivbxO3iu8NKbfPNe7VTz9ZMk88RZTu5QsybxeQtk7qpTAOzGSjTxSwO27mGIjPO7OC7x7FoW8wJayvI2uJzttxqk84H4wOUtlfbxblAw8uTtCPIO3Vzxkz9k8ENwfvfQYuLvHFNQ8LvatPF65ojzPLHA8+RyCvK3Kmjx27wk8Dcn2PARatDv3tBc8hkLzPEOz5jyQSoe8gU/tPMRmhzzp2wU90shPPBv2oLsNQMA8jTdevIftMTt/Xsw7MMQdPICjBT012tS7SLewvJBtuDuevZM8LyojPa6HxjtOAd07v9mGusZXqDoPqKo8qdeUvETnW7y5occ5pOSOvPPkwjsDN4O8Mk85vKnXlDtp06O7kZDpO6GuNDtRFAY9lAkYPGHNdDx2Afc7RRtROy5/5LyUoxI9mu0+u/dOEryrYrC867vivJp29TtVbZG8SVGrO0im7LnhsqU80frfPL/IwryBT+07/+/kPLZ8sTwoNbg7ZkiIOxadlbxlnUm68RbTuxkX7Tu/cwG7aqGTPO8CAbzTYsq6AIpfvA50tbzllOc7s3rMO0SBVjzXzJm8eZ3Wu4vgtzwPDrA8W6b5uwJpEzwLtaQ81pgkPJuqarxmro288369u48WkjwREBU9JP/dPJ69kzvw4t27h3bouxhrBbwrNx29F9EKPFmSJ7v8px08Tt6rvEJthLxon648UYz4u61TUTz4lPQ7ERAVuhwqFrzfSjs8RRtRO6lxD7zHelm87lfCu10O5LrXMh886YftvL9iPTxCf/E6MZKNOmAhDb2diZ47eRSgPBfRCrznlsw5MiwIvHW7FD3tI807uG3SPE7eqzx1VY864TtcO3zTMDw7EhS8c+0kPLr47TvUDQm8domEvEi3MLruaAa7tUi8u4FgsTwbkBu6pQfAvEJthLwDnQg8S1OQO55GSrxZLCK8nkZKvFXTFr01dM+8W6Z5vO+u6Luh0eW8rofGvFsdw7x7KHK8sN5svCFAzbo/0SS8f9UVu7Qli7wr0Re95E4FvSg1ODok/907AAGpPHQhGrwtS++71pgkvCtazjsSzcC7exYFPLVZgLzZmom7W6Z5PHr0fLtn9O86oUivukvcRrzjPcE8a8REPAei+zoBNZ685aUrPNBg5bqeIxk8FJuwPPdOkrtUOZy8GRftO4KD4rz/72Q7ERCVu8WJODy5O8I5L7NZuxJECjxFkpq8Uq4AOy2fh7wY9Du8GRdtu48o/7mHdug803MOvCUQIrw2hZM8v+tzvE54pruyI6a6exYFvDXrGDwNQEA8zyxwO7c53TwUJGe8Wk9Tu6ouu7yqCwo8vi7IvNe71TxB04m8domEvKTkDrzsidK8+nOovLfT1zr11eM7SVErO3EOcbzqMqw74Tvcut4WRrz5pbi8oznQvMi/Er0aS+I87lfCvK+qdztd6zI83eJQPFy3vbyACQu9/8wzO/k/s7weG7e8906SPA3J9jw8NUU8TUQxPfEWU7wjH4E8J3gMPC72LTp6SJU8exaFOXBiibyf4MS6EXYaO3DIjjy61by7ACRaO5NvnTvMGB48Dw6wPFEUBr30j4E7niMZvIZC87s7EpS8OZnlPJZxgrxug9U7/DDUvNrxL7yV14e3E2c7PBdaQTwT8HE8oIuDPGIB6rvMB9o6cR+1OwbCHrylfgm8z6M5vIiqXbxFG1G8a9WIPItp7rpGT8Y838GEvAoK5jyAG3g7xRJvPPxBGLzJWQ28XYWtO85vRLp0IZq8cR81vc7mDb28PSe89LKyuig1uDyxEuK8GlwmPIbKgLwHGcW7/qkCvC8ZXzzSyE89F8BGOxPw8Tx+Ktc8BkvVurXiNryRkOk8jyj/OcKH0zp69Pw8apDPPFuUjLwPDrC8xuBeuD43KrxuYKQ7qXGPvF0OZDx1VQ88VVzNvD9rn7ushWE7EZlLvSL9+DrHi528dzXsu3k30bzeFka7hrm8vD3gAz1/Xsy80D20PNPZE7sorAG86WS8u2Y3xDtvHVC7PKwOO5DkAT3KOeo8c+0kvI+fyLuY61k8SKbsO4TrzLrrZqE87O9XvMkF9Tynb6q847SKvBjjdzyhSK88zTtPPNNzjjsvGV87UQPCvMD8t7stn4e7GRftPBQkZ7x4eiW7sqzcu3ufO7yAG3g8OHa0u0T4n7wcxJC7r6r3vAbCnrth3rg7BxnFumqQzzyXyCi8V8Q3vEPEqjyIu6E8Ac+YvGR6GLulkHY8um83PMqNgrv5pTi8N7kIPOhTeLy6TIY8B5COvDLGArvEzAy9IbcWvIUfQjxQ4BC7B/aTvCfwfrz15ie8ucR4PD1pursLtSS8AgMOOzIsiLv0srI7Q01hPCvRF7vySsg6O5tKunh6JTvCZCI7xuDevLc53btvLhQ8/pi+PJU9Dbugi4O8Qn/xvLpMhrth3ji8n/GIPKouu7tBS3y853MbPGAQyTt27wk7iokRO8d62bzZRnG7sN5svAG+1Lqvqve8JGXjur0Ll7tCf/E75/xRPIWFx7wgDNi8ucT4OZNvHb2nktu8qrfxuyR2J7zWh2A6juKcPDhlcLx/1RU9IAxYPGJ4szylB8C8qfrFO276HjuWcQK9QdOJvCUQIjzjo8a8SeslvBrCKztCf/E66MrBOx1eCz2Xt+Q66YdtvKg9mrrLSq47fFznO1uUjDsoNTg8QyqwuzH4Ejz/Zi67A8A5uKg9GrtFkhq862ahOzSmXzkMDEs8q+vmvNVkLzwc1n28mu0+vCbekTyCg+K7ekgVvO8CAT2yRtc8apBPu1b2R7zUp4M8VW2RvPc9zrx69Hw753ObvCcSB71sG+u8OwHQuv67b7zLSi65HrWxO0ZPRrxmwPq7t7CmPGxvAzygnfC8oIsDvKY7tbwZF+07p2+qvOnbhbv0oW47/2auuThlcDwIxIM8n/EIO6ijH7vHetk7uRiRPGUDT7pgh5I85shcPpGQabykShS7FWmgPPjojDvJ8wc8mlPEOY2uJzt7FoW7HNb9O7rVvDzKjQI80NcuuqvINbvNTBO8TgFdvEJ/cbzEZoe8SVGrvMvkqLyHdui7P2ufvBSbMDw0t6O82GaUPOLmGrxSNze8KVjpuwizPzwqjN48Xh8ovE4B3TtiAeo8azsOO8eLnbyO4py7x/GiPIvgNzzvi7c8BFq0O/dOEj1fU5282ZoJPCL9+LqyIyY8IoUGPNI/mbwKpGC7EkQKuzrN2jwVzyU7QpA1vLIjpjwi64s8HYE8u6eSW7yryLU8yK5OOzysjjwi6wu8GsIrOu7xPDwCaRO8dzVsPP/vZLwT3oQ8cQ7xvOJv0TtWBww8hlM3PBPeBDxT9OK71pgkPPSysrugiwO90GDlvHOHHz3xfNg8904SPVpglzzmP6a7Cgrmu9/BBLyH7bG85QsxvVSfIb2Xt2Q8paG6vOqYsTos9Mi8nqxPu8wHWjuYhdS7GAWAvCIOvTp/bxA8j7CMPG1P4Dxd67I7xxRUvOM9wbxMhwU9Kp0iPfF82LvQYOU6XkJZPBxNx7y0nX28B5COO8FT3rp4eiW8R/oEvSfw/jtC9rq8n/GIux3nQTw8WPY8LBf6uzSmXzzSPxm88rDNvDysDjwyPnW7tdFyPBLNwDo8WHa8bPi5vOO0CrylGAQ8YgFqvEFLfDy7LOO7TIeFPAHPmDv3YP+6/+9kPBKqjzt5rpo8VJ+hvE7eKzyc3t88P2sfvLQUR7wJ1vC6exaFvD6dr7zNO888i+A3ulwuhzuF/JC8gKMFveoyLLxqBxk7YgFquws+2zwOUYS8agcZvGJ4M71AjtC747QKvAizP73UH3a7LvatPJBtuLzEzIy8bG8DvJEHM75E59s7zbIYPObZIL2uZJW7WRveugblTzy6TIa802JKvD9rH7xlA088QAWavIFP7bwL2FW8vqWRu0ZgijyRkGm7ZGnUvIeHLD1c2m48THbBPPkcAr1NzWc8+JT0uulkvLvXMp+7lU96u7kYET1xhTo8e3wKvItGPTxb+hG87mgGPWqhk7uhrrQ73rBAPCbNTT13rDW8K8DTus8s8DsNt4k8gpQmPLES4ryyvSA8lcbDO60woDyLVwE9BFq0u+cNFj3C7Vi8UXoLPDYOyryQ0z083+S1Ox34hTzEzIw7pX4Ju6ouuzxIpmw8w5iXuylYaTy5sgu9Js3NOo+fyLyjFp+8MMSdvOROBb2n+OA7b7fKOeIJzDoNpkW8WsYct7SdfTxXxLc7TO2KO3YB9zynktu7OkSkPKnXFLvtRv47AJujuzGSDT0twjg8AgOOO4d26DvpZDy8lAkYPI5r0zcGS9W8OGXwu9xIVjyH7TG9IUDNuiqMXrwb9qA79I+BPL1xHLuVPY07MOfOO0ztCruvMoW8BuXPu4AbeLyIRNg8uG3SPO5XQjuFH0K8zm9EPEAoSz0tKL652ZqJOgABqbwsjsM8mlPEPLewpjsVWNw8OGXwOlYHjLzfwQQ81iFbOyJ0Qj3d85S7cQ7xvIqswjxKhSC7906SvAFYz72xiau8LAWNPB1eCz09jGu72ZoJPfDiXTwPDrA8CYGvvNH6XzxTa6y8+RwCvY8of7xxDnG8Ef/QvJ9p+zqh0eU8a16/OzBN1LyDLiE9PFh2u+0jTbxLUxA9ZZ3JvItXgbqL4Dc8BuXPvKnXFDzmPyY8k/hTOlum+bqAksG8OZnluPmluLxRnTy6/KcdvKAUOrzRcSm8fqEgPcTeebzeOXc8KCR0OnN2W7xRA0K8Wsacu+M9wToyLIi8mTATu21P4LuadvW8Dtq6vPmlODsjqLe88ieXPJEHszySoa08U/RiPNQNCbwb9qC8bG+DOXW7FL0OdLW7Tc3nvG8dULsAJNo7fNMwO7sJMr2O4hy85ZTnuwAkWjw+Nyq8rcoaO+8lsrvx86E8U/TivGUUkzp6SJW8lT0NvWz4uTzeFka6qguKvIKD4rt/1ZU8LBf6vD6dr7es/Ko7qWBLvIlVHDxwUUU6Jt4RvRJEijnRcSk88235PGvVCL3zbfm8DaZFO+7xvLs3qES8oznQO9XKNDxZLKK8IIMhvComWb0CAw48fDk2O+nbBb29C5e8ogVbu1EUBryYhdS7OTPgOul1AD25sgs7i1cBPBYmzLtSroA8hfyQvP3bErz9h/o82ZoJO7/ZhjxtT+A8UZ28uzaFk7wJ1nA6dd7FPGg5Kbwb9iC8psRrvBXyVjzGRuS8uAfNu0+smzvFAAK96FN4vC2fhzy65oC7tgXou/9mLjxMELw8GSgxPRBlVjxDxCq80j8ZveinkDxHgzu70j8ZvPGNnDyPn0i8Vn9+urXR8ju10fI7sRJiPDBemLt8OTa8tJ39O4ne0rsaXKa7t0ohPHQhGrdYXjI824sqvDw1RT2/2YY8E/BxPIUOfjv9dQ08PM8/PMwYHrwwXpi7nqxPPM8aA7w+wOC7ROdbO79iPTxVbRE8U45dPOOjRjxwYok8ME1Uu1SfIbyifKQ8UXqLPI85wzsITTq8R+lAPMRVQzzcv58892B/Oqg9mjw3MXu7P9EkvM6AiLyx7zA8eHolPLYWLLugFLq8AJsjvEOzZjk6RKQ8uRgRPXVVjzw0HSk9PWk6PLss47spzzK93rBAvJpTxDun+OC7OTPgvEa1yzvAH+k5fZDcOid4jLuN0di8N7kIPPe0F7wVaSC8zxoDvJVgvrvUpwO9dd7FPKUHQLxn4oI7Ng7KPIydYzzZRvE8LTkCu3bvCTy10fK7QAWaPGHeOLu6+O27omvgO8Rmh7xrXj87AzeDvORg8jnGRuS8UEYWPLPg0TvYZpQ9FJuwPLC7O7xug1U8bvoevAnW8DvxFtM8kEoHPDxYdrzcWZq8n3q/O94nCjvZI0C82yUlvayWpbyHh6y7ME1UO9b+KTzbFGG89oCiPFpgFzzhTKA84gnMPKgsVjyia+C7XNpuPHxc5zyDLqG8ukyGvKqUQLwG5U88wB/pO+B+ML2O4py8MOdOPHt8irsDnYg6rv6PumJ4szzuV0I80qWePKTkDj14A9y8fqEgu9DXLjykbUU7yEhJvLYFaLyfVw68",
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
            self.wfile.write(b"Could not parse prompt.")
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
    # Import OpenAI so that get_package_version() can capture the version from the
    # system module. OpenAI does not have a package version in v0.
    import openai

    return get_package_version_tuple("openai")


@pytest.fixture(scope="session")
def openai_version():
    return get_openai_version()


if __name__ == "__main__":
    _MockExternalOpenAIServer = MockExternalOpenAIServer()
    with MockExternalOpenAIServer() as server:
        print(f"MockExternalOpenAIServer serving on port {server.port!s}")
        while True:
            pass  # Serve forever
