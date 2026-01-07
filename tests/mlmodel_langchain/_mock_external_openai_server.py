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
