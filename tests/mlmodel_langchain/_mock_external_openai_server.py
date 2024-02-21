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
    ],
}
RESPONSES_V1 = {
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
                    "embedding": "0TB/Ov96cDsiAKC8oBytvE/gdrsckEQ6CG5svFFCLDz4Vr+7jCAqvXdNdzx16EY8T5m2vJtdLLxfhxM7gEDzO8tQkzzAITe8b08bPIYd5DzO07O8593cO8+EDrsRy4I7jI2/vAcnrDvjPMw7ElaIvB/qFD2P5w+9kJvlPMLKrLzMl1O8DAwCvAxTwjuP54+7OsMIuu26TbxXjLI8ByesvHCWWzydczc7dF3BO6CJwjkzeQK9vQssPI42NTqPVKW8REEKO7GVjzx42Hw8xXOiuzhh07wrYLE8JDwAvS0Jp7oezKS8zxr0PEs/5jwNBB28NFMtvMKGZzt1wvG8pFAoPInkSbyZjuE7AmirOx1BHzzDN0K8cSHhPNCl+Ty5k2u8yp84vDjOaLzyDLk8jlyKO1FrfLywd587qi0ZPN0QNryGYak8fFC9vLZ94LuRkIU8x7L9OwHdJTwDhpu7sKDvPLajtbx7Ms28eRzCOp2ZjDoRpa07ZNx5PGMoJLzrL8g7KkJBvJvwFjzEwke7RK4fvWlyKrxWAS281c4UvNX3ZLz0SBm8+k7au3YsDDzoaGI7+ZqEPPatSTuNPpq8vXjBPGHsQ7yLb8+8D48iO5OxcLsb32k80KX5O+ShfLtErp+8L5SsPP07FT3C8IE8eYnXvH/5MjwHupY6EK0SvWVkhLzW7AS826uFvPGfIz2dczc8z8tOPB+Aejufa9K8bsSVPHj+UTlFOaU8kZAFvA5L3bwv22w86YZSPG/ihTxOv4u82QKQPDu7ozwqhoY8hJJevIBA8ztSYBy8EsMdPBpUZDxs9co7TTQGvH0q6Do3hyg8fJ9iO2wboDwot7s7vryGvHrNnLrLUBO8SSnbu4cSBL2e4Ew8JTSbPOmG0jxdJV47arlqvHBti7zZmHW8q0sJPIZhKb3mcMc8glZ+vOqkwjuBoqi7lcSAPKb5nbw2/KK8GMnevE00BjylAQM8y3njPDW43brZ3Do6O06OPERBirtcmlg8D2lNvKUBAzzzcek84mKhPMhjWDy0GDC/PmSZu8VzIjxfYT480nTEu3j+UTyTG4s8y1CTPIPeiLu0PoU8YruOu2z1SjyiFEi7ZY1UvPZeJLzV92S8K83Guq47v7weObq8PUYpPMM3QrwUKM48nA4HvFVQUrw4OIM8jYVaOuisJ7l+H4i8TTQGOoVDuTxbLUO8/1GgPMZrPTx16Ea6MIxHPR2uNDzLKr67QgUqPCLayjuONrU8z/EjvEK2hLxGpjo7P8nJvHvFN7zLeeM7frXtPDN8/Tv4Vr+7rmGUu0amujxnyTS8ApF7PPZeJDyvFWo7AmirO6rAAz14/tE7syAVu20TOzsMD326gsCYOj+CiTqDB1k8rs6pvDM1vTwkFqu8+2xKPG9Pm7x+bi28XHGIurhyALzDEW2802xfvEJyvzzuHAM9JfDVPGClA7v8ZGW8fQGYPJgDXDxITzA7QA2PvA3A17wwspw8WPnHu5Xt0Lz7bMo6pL29uZFMwDutiuQ8I4slPN7BkLyS18W7q0sJPTGqtzvR6b67WKoiPPME1Dwx0Iy7EhLDO5QTJrzT/0m8nFVHO8ccmDwEzVu70uFZvGVkBD3xnyM9ZWf/vHOsZjuwCgq8VeM8veCT1jwUKM46hxIEvfX87ruFQ7k7dMrWPDN8fby9MYE8RcwPPKnp0zy7z0u8vFpRPB+Aeju9NHy8FQL5O+HXG7xljVS8TBaWPPOXvjrrwrI8UUIsvH5I2DsCaKu70TB/PKLFIrxowU889xJ6OZ2ZDLyZIcy7poyIPOrKl7zGkZI8c6zmvAzmrLwp/vs6TiwhOuchIrxJ2jU8vIAmvNqNFb1gEpk7J5lLuxtJBLxy0rs7FLu4vMJdF70xZvK89q3JuinVqzxLP2Y7frXtuqUBAzvVis+8tD6FvKGnMjykl2i7TiwhvZDBujx0Dhy87x9+vOAAbDoWs9O7qi2ZO9kCkLyF1iO8bsSVvAKR+7vNSK66O7ujuyn7gLz+M7A7W+YCPYooDzvmA7I72QKQPBfRQ7wSEkO4DQQdPJvwFjyZIcy8uAhmOsPoHLwP1uK52klQPBLDHbxxIWE8prXYPNCl+Tx764y6powIPV5DzrzfTBa79WYJvag4+TsaBb+8ysUNOyn7gDyBoig8BnZRvIXWI7uJCh88eYnXPJi0tjyNPho7OgpJvO5rqLzaIAC86PtMvBaKgzywM1q8LQmnu59CArq0PgU95J4BPNwYGz1pcqo7eRzCvGEwCb24coA8N4coPFEc17uj45K8OPS9u9XOlDwEzVu8gIQ4PHC8MDz4w1S8OgpJPEbt+jzchbC80S0EPI2FWjx9Kmg8WD0NOgYJvLkeps887HMNO1V2p7qOXAq8LBEMO4OaQ7zviRi9jNT/u8C0IbyRkAU8BS8RPaKBXTxV4zw8O06OOylolrmkl+g7T+B2vOCT1juKvnS8hJLeu29Pm7xVvWe8jNT/u3Xoxjw++n68f/myOzLIJ7vEnHK7H1eqO2z1SjxOVfE7z/GjvAqEd7xUWDe7sDNaPJEma7rLvSi8W+YCvUkACzzXDfA7FChOu5JqsLyY2gs8YKUDPN/fAL3fdWY8ZCA/OyG82jx0XcG8OgpJOee0DLzbq4U8qenTO6Zms7wHupa87HONPB71dLuaGec6KSTRuw9pTbuTsfA56+gHPN2jIDwpaBa7y1ATPKAcrTxx2iC6GyMvOug/EjwdG8o8q7geu9pJ0Ls4zmi7X87TvGq5arzl5UE902xfPI2rr7pS84Y8y1CTvHx2ErzQpfm8yGPYvHckJ7ynF4472iP7uk/g9juhOh07k4ggPKmiEzwXgh66JujwOWHGbrwuJ5e6637tu2h6j7sIAdc7/RVAO3CWWzyvWa88CEWcO3x2Ejxtz/U7zbVDvPc4z7xkRhS6mNqLuw/8NzzMl1M8kHIVuxz92Two3ZA8tYVFPRu2mTsF60u8bPVKPGB/LjzgJsG79WYJvEGYlDto56S5RBs1O16wYzwnLDa8vrwGvVkXuDxQJLw7Juhwu92joLxFYnW83X3LO+LPtrsKhPe7vZ6WvCe/IL1rRPC8mAPcvLGVj7zem7u7nS9yvPGfI70gCAW9CWMMPArQobzgaga8hvSTu5UxFr3JFLO8OlluPAG30DycVUc8EBoovGwbILxGVxU8cSHhO4zUf7uLSfq8aOckPN8I0btNDrE8VpQXuqRQqDwp+4C75nDHu70xAT0iACA7rqhUPEHnuTwOcTK8YVnZO8Ok1zv4Vr86WsgSvBtyVLzJ7t07LBEMvH9mSLy2o7U5OsMIPIMHWTsZ5048kC7QPAPzsDxYPY28V7KHOYyNPz0++n68z/GjPHC8MLlzgxa8mSHMPG/iBT21NqA8BuNmvA2XB725aps5xAaNvC8BQjzOZp48q3RZuiP4Ortwllu8nXO3vAqEdzrtlPi6w+icu8oyozvA+2G8+XSvOFxLs7w6w4i5uh7xOD5kmTyxUUq8wzfCu3Eh4byOXIq85AuXOcMRbbyJ5Em93TYLvV5DTrztus079EgZvMGsPDymtVi8GMleO5dPhryjMji74mKhO/olCr3aIAC7ye5dPN9MljwF60s8eNUBPUhPsDsfgPo7X4eTO/mdfzvem7u7jRhFvG8L1rw7KLm84LmrPKRQqDwx0Aw9P4KJuzVLSDsJ+XE8W+l9OXjVAbxE12+7i29POzkSLrzG/qe88VteuT9cNDrKnzg8B7qWO7dUELxbLcM7ysWNOxyQRDwdrjQ8aFS6PKVIw7sGdtE8U+shPNtnQDsfgHq8nS9yu7ebULuwoG88cxYBPJXHezytQ6Q8vKl2vGz1SrsvlCw702zfPCQWKzx2c0w7URzXu2tEcLpXSO07cbRLvIHL+Lv1QDS8JceFOotJery79aC8HUEfPCLaSrwkPAC9YKWDu23PdbnNSC49q7iePHvrDDwFfrY82W+lO8nu3TsXgp48lymxvO+JmLoeXw89c/CruqQq07us/168dKGGOu8ffjszeYK7ZEYUvdpJ0Lolg8A8YKUDu70LrLwkqZU7x68CvZFMQDx+tW07iQqfvDvkc7wGCTw8OlnuvAxTQjz9O5W8ULemPFEc1zwo3RC8mAPcOggBV7thMAk8mANcurZ9YLyNhdo8H1eqvJG5VTy9NHw8FxWJu4gz77pCcj+7uf2FvE8GzDyXKbG8kxuLO/Gfo7tvT5s84+0mvOe0DDywoO+7ty47u2c2yrplZIS8TPDAPKAcLTyfkSe7TcrruyjdkLyVxIC8DHkXvYMtLjugRf075AuXvF5pIzz0SJm7Hjk6POxzDTzHia08zfmIu5wOhzxG7fo83RC2vM8a9Lv2h3Q8sVFKPG05kLzAtKE8Pvr+uryp9rpP4PY7MB8yvABwkLz4Vr87mhnnOtkCkDvG/qe7gaIoPHOs5jyzIJU8v3DcO50vcrwKPbe8xif4PLU2ILt/jB28mj+8OqySSbxduEg8uEwrvI6jSru8E5G7k7HwvO5rKLwYyd465imHOtSwpDs5pRi8prXYvHo6MjqGHeS8BKSLO9YV1Tu8gCa8zUiuuxsjLzv3Eno8sVHKuk9KETygr5e71w3wu9RDjzkRy4K8EWFovH7bwruybzo9BpwmPNczxTuVxAC8PUYpvDUECL1XH528pJfougVYYToMeZc7kHKVPCnVKzu0PoU8/jOwuvEyDjyI7C686D+SvAwMgrouugG8dXuxPNX35LvxW968M6JSO8yXUzs1cZ08s7Z6Ow/8tztsiDW8kxuLu7HktLwSw528JKmVOmhUOjzrfm084GqGvAwMgrseXw883RC2O2VkBDsYXMm8JYNAOoIPvry2EMs8bRM7vC4nlztFYnU8thDLvH5I2Dw+0S685imHPNcN8DywM1o8mLS2O6Pjkrq5Jta7jCCquSVdazz46Sm6cSFhO2uuCjz+oEW8tqO1vKcXjryONrU6xU3NvD/vHrwrOtw75KH8PKJYjTxPShG9wdKRvGA76byl2y0844ARPFProbzFc6K6AbdQvEMjmjpgpQM8s/q/vMevgrsamKk8Sz9mPNRDD7qmtdg8kSZrPvVmCbywCoo71hXVPDFm8jwFWGE8BetLPDRTrbtBweQ7UCS8O89eObyNhdq7GMlevBeCnjvnjrc768IyPAeUwbxlZ/+84ovxvOxzjbzRLYQ7/1GgvKHNh7wD87C8ukRGPCMekDtQkVG8z4SOu32UAj29npa6IbxavJhHobt+tW07F9HDPFo1qLwzolK85yEiPWq5ajy9MQE905I0uxAaqLwK0KG8Jg5Gu23P9TstxWE7BycsPI2F2rv7sA+94ADsO8ey/TyIWcS7oEV9PImdiTzIOgg9aS5lPMu9qLy4ucA8ZlyfPPtsSrza+iq8c6xmu9MlHz2QLtC7FUa+POo3rbygRX27/jMwvWr9L7sHupa6RNdvvAvukbwmobC7LrqBu2HG7jrwgbO8AUo7vLICJTxUxcw73X3LPGku5TxI4pq8iigPvJOIILxNyuu8S6kAvUSuH700Uy08XJpYvI6jSrwT4Y28OlnuOzowHrwcau+5X85TPP6gRTwyWxI8Nmm4Ow3AVzxVvee7AUo7vFZuwrvdNos8l7wbPKrAg7t3TXe8baYlPDdD47tUMmI87HONOw5xsrt9lAK92iCAvMevArotxeE7h6jpvAG30Du79aC8ApH7uYjsrjvcX1u8l5bGOmz1Srwxqje8I/g6PHe3kbrRMH+8P++eu30qaDx4/lE8MT0iverKlzpunkA79xL6POj7TDzAIbc7fSpoPKPjkjvJFDM7nHucu5JqsLt9vVI7piJuvD7RLjzaI3u84LkrvGTc+bweps88Ru36vBD00rvuayg6NxoTvfmaBLpANl+8PG/5u2yINT3D6Jy7LBEMvMsqvrzoaOI7Im01uzN5grxCBao75eXBPMYn+LtRQiy9k7HwvHivLL789088ehRdPOSegbwi2ko8+9lfO4ZhKTy+vIY8ctI7O3jY/Dux5LS6z/GjvJqDAbxrrgq9MWbyuyQ8gLzviRi8ygzOtjVxHT15YIc8hLgzPbMglbvWWZo7zmYeux9XqjtGE1C87muoO4kKHz0kPAC7Qee5vNNsX7za+qq8UdUWPXMWgTyEkt48HvX0u3yfYjvfTBa9/jMwvNSwpDwhvNo8WjUoPIhZRDzYUTW8e8W3vGJ3ybs6MJ4818Yvu2ASmTz9FUC83PJFPHtYorvO0zO7jRjFumHG7jzHia08tqO1u6/smTyM+lS7JNLlu1iqIrzkoXy8RTmlu0naNbzZmPW7DAwCumyINbxG7fo7fkhYvGOVuTyMICq8HvX0vAo9N7xWJwK9ZCC/O24xqzu9nha9xMLHPK2K5DodrjS8sAqKvIzUfzzpGT08cdogPHPwK7z+MzA8f4wdvIE1Ezzp8+e8U+uhvG7ElTwVRr68pFCou35urbwJY4w7qDh5PCTS5TsV2ag8pCpTvA5LXbxFOSU6uN+VPAljjLwrzca6fQEYPfFbXrz5dK88vTT8O34fCD2kUKi8t1QQvD0g1DtpLuU85463PL0xgTx0ytY8RleVuw3AV7wHuha7aFS6ukIFKj1/Zkg82iP7vOldAjyVMZa7pCpTOjaPjb2aGee8qpouOXrNnDwIRRw8zNsYPUOQr7tHMcA7wPthujowHjxQt6Y7PqtZvC/b7DuyAqW7l08GPdfGr7xQt6Y8NxqTvJ9r0rvTJZ88uf0FuyMeELzPy048hxKEvKu4nrxUWDc8AY6AvGtE8DxTp1w77ti9u6jxuLxKtOC8S9JQu0K2BLyEuDO6UmCcPOBqBr1iUXQ8yGNYPDEXzbzleKw8KfuAPIq+9LuJnQm98KeIuzW4XTzG/ic7uh7xPEA23zuixaK83sGQvJaeK71KR8u8fHaSPG05kDubXSy74vWLPHCW2zwb32m7vKn2O7XJCjxksyk7KWgWvbgI5jwBjgC8U6dcPM/LTryhp7I8AAb2PPwdpTsnUou8jja1PJ+RJ7wOS908P+8evZ4kkjwFLxG8GXq5vNaoPzxG7Xo8TlXxvGhUurw0wMK6M+YXvKZmszzgaoY8cxYBvPl0rztHxCq8Z8k0va/sGbyzIJU857SMPF5DTrw/gok7ipWkPDpZbrrHiS27QnK/PEhPsDxLqQC9j1SlvM7Ts70J+fE8nKTsu7qIi7wp1as8uEyruZmOYTx+tW282o0VvLONKrt2maG8m8pBu/FbXryqw348K83GvG3P9bvmKQc9d5G8PM5Aybsc/Vm7OlnuOp4kkrye4Ey8wLShO0fEKry6HvE7f4wdvZAuULsQh725LrqBvLjflTtmXB+9VicCvEbt+jzrL8g7NUvIux7MpDuONrU8woZnvBLDnTx42Py861WdvNlvpTzguSs8GedOu1zenTqtQyQ76GjiOrZ94DwQ9FI8lDz2O7lqmzzF4Le8jPpUu/VmibzntIy8mY5hvJCbZbphxm67vO07veMW9zzZAhC8/sYaPdQdurv1/G47pFAoOxHLgrwBjgC8sAqKuwjYhryWnqu7AkJWvG05EDyRTMA8mY7hPOxNuLh6OjK8YnfJPEltIL3Rmhk93TYLPXXC8TuRJuu81ffkOXxQvTxhnR48frXtOurKlzrM25i7UdWWOyjdEL3hRDG8DktdO7wTkTxtORA8RTklOy5Q57tDkK86ULemPHsyTTzgJkE8635tPNXOlLtduEg7W+aCuxPhjTp5iVe8/PfPvCqvVjyLSXo78wRUOuJioTwFLxG7E3dzPBtJBL3Hsv04v3DcPGK7jjtrrgq9qaITPcPoHLxIvMU7+ZoEPRJWiLyF1qM7E3fzOEIFqjttz3W8XrDjPOho4rsM5qw8AvuVu/fLubsX0cO8RhPQOaySSTjuHIM77kVTPLpERrxk3Hk9JDwAPGqQmrt8n2I8YcZuPLU2oDzPXrk8oK8XPO26TbzA++G8fJ9iu5o/vDuvf4S8ODgDvTFm8rtDI5q7Nd6yvIeoabzBP6e8iMbZPOtVnTw6WW48GXq5PLxa0TuAqo28vKl2vNbsBDwJY4w7yDqIvAwP/bys/948frVtuxorlLyLs5S8SSlbO1OnXDsk0mW7fSrou68V6rtHxCo8CzXSPFvmAjvVO6q8UGgBvfmahDsI2IY8BVjhvAljjLsiR+C8",
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
            self.wfile.write(("Unknown Prompt:\n%s" % prompt).encode("utf-8"))
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
    import openai  # noqa: F401; pylint: disable=W0611

    return get_package_version_tuple("openai")


@pytest.fixture(scope="session")
def openai_version():
    return get_openai_version()


if __name__ == "__main__":
    _MockExternalOpenAIServer = MockExternalOpenAIServer()
    with MockExternalOpenAIServer() as server:
        print("MockExternalOpenAIServer serving on port %s" % str(server.port))
        while True:
            pass  # Serve forever
