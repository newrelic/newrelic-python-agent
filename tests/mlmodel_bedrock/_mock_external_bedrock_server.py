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
import re

from testing_support.mock_external_http_server import MockExternalHTTPServer

# This defines an external server test apps can make requests to instead of
# the real Bedrock backend. This provides 3 features:
#
# 1) This removes dependencies on external websites.
# 2) Provides a better mechanism for making an external call in a test app than
#    simple calling another endpoint the test app makes available because this
#    server will not be instrumented meaning we don't have to sort through
#    transactions to separate the ones created in the test app and the ones
#    created by an external call.
# 3) This app runs on a separate thread meaning it won't block the test app.

RESPONSES = {
    "amazon.titan-text-express-v1::What is 212 degrees Fahrenheit converted to Celsius?": [
        {"content-type": "application/json", "x-amzn-requestid": "660d4de9-6804-460e-8556-4ab2a019d1e3"},
        {
            "inputTextTokenCount": 12,
            "results": [
                {
                    "tokenCount": 55,
                    "outputText": "\nUse the formula,\n\u00b0C = (\u00b0F - 32) x 5/9\n= 212 x 5/9\n= 100 degrees Celsius\n212 degrees Fahrenheit is 100 degrees Celsius.",
                    "completionReason": "FINISH",
                }
            ],
        },
    ],
    "ai21.j2-mid-v1::What is 212 degrees Fahrenheit converted to Celsius?": [
        {"content-type": "application/json", "x-amzn-requestid": "3bf1bb6b-b6f0-4901-85a1-2fa0e814440e"},
        {
            "id": 1234,
            "prompt": {
                "text": "What is 212 degrees Fahrenheit converted to Celsius?",
                "tokens": [
                    {
                        "generatedToken": {
                            "token": "\u2581What\u2581is",
                            "logprob": -7.446773529052734,
                            "raw_logprob": -7.446773529052734,
                        },
                        "topTokens": None,
                        "textRange": {"start": 0, "end": 7},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581",
                            "logprob": -3.8046724796295166,
                            "raw_logprob": -3.8046724796295166,
                        },
                        "topTokens": None,
                        "textRange": {"start": 7, "end": 8},
                    },
                    {
                        "generatedToken": {
                            "token": "212",
                            "logprob": -9.287349700927734,
                            "raw_logprob": -9.287349700927734,
                        },
                        "topTokens": None,
                        "textRange": {"start": 8, "end": 11},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581degrees\u2581Fahrenheit",
                            "logprob": -7.953181743621826,
                            "raw_logprob": -7.953181743621826,
                        },
                        "topTokens": None,
                        "textRange": {"start": 11, "end": 30},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581converted\u2581to",
                            "logprob": -6.168096542358398,
                            "raw_logprob": -6.168096542358398,
                        },
                        "topTokens": None,
                        "textRange": {"start": 30, "end": 43},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581Celsius",
                            "logprob": -0.09790332615375519,
                            "raw_logprob": -0.09790332615375519,
                        },
                        "topTokens": None,
                        "textRange": {"start": 43, "end": 51},
                    },
                    {
                        "generatedToken": {
                            "token": "?",
                            "logprob": -6.5795369148254395,
                            "raw_logprob": -6.5795369148254395,
                        },
                        "topTokens": None,
                        "textRange": {"start": 51, "end": 52},
                    },
                ],
            },
            "completions": [
                {
                    "data": {
                        "text": "\n212 degrees Fahrenheit is equal to 100 degrees Celsius.",
                        "tokens": [
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -1.6689286894688848e-06,
                                    "raw_logprob": -0.00015984688070602715,
                                },
                                "topTokens": None,
                                "textRange": {"start": 0, "end": 1},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581",
                                    "logprob": -0.03473362699151039,
                                    "raw_logprob": -0.11261807382106781,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1, "end": 1},
                            },
                            {
                                "generatedToken": {
                                    "token": "212",
                                    "logprob": -0.003316262038424611,
                                    "raw_logprob": -0.019686665385961533,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1, "end": 4},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581degrees\u2581Fahrenheit",
                                    "logprob": -0.003579758107662201,
                                    "raw_logprob": -0.03144374489784241,
                                },
                                "topTokens": None,
                                "textRange": {"start": 4, "end": 23},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581is\u2581equal\u2581to",
                                    "logprob": -0.0027733694296330214,
                                    "raw_logprob": -0.027207009494304657,
                                },
                                "topTokens": None,
                                "textRange": {"start": 23, "end": 35},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581",
                                    "logprob": -0.0003392120997887105,
                                    "raw_logprob": -0.005458095110952854,
                                },
                                "topTokens": None,
                                "textRange": {"start": 35, "end": 36},
                            },
                            {
                                "generatedToken": {
                                    "token": "100",
                                    "logprob": -2.145764938177308e-06,
                                    "raw_logprob": -0.00012730741582345217,
                                },
                                "topTokens": None,
                                "textRange": {"start": 36, "end": 39},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581degrees\u2581Celsius",
                                    "logprob": -0.31207239627838135,
                                    "raw_logprob": -0.402545303106308,
                                },
                                "topTokens": None,
                                "textRange": {"start": 39, "end": 55},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.023684674873948097,
                                    "raw_logprob": -0.0769972875714302,
                                },
                                "topTokens": None,
                                "textRange": {"start": 55, "end": 56},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|endoftext|>",
                                    "logprob": -0.0073706600815057755,
                                    "raw_logprob": -0.06265579164028168,
                                },
                                "topTokens": None,
                                "textRange": {"start": 56, "end": 56},
                            },
                        ],
                    },
                    "finishReason": {"reason": "endoftext"},
                }
            ],
        },
    ],
}

MODEL_PATH_RE = re.compile(r"/model/([^/]+)/invoke")


def simple_get(self):
    content_len = int(self.headers.get("content-length"))
    content = json.loads(self.rfile.read(content_len).decode("utf-8"))

    model = MODEL_PATH_RE.match(self.path).group(1)
    prompt = extract_shortened_prompt(content, model)
    if not prompt:
        self.send_response(500)
        self.end_headers()
        self.wfile.write("Could not parse prompt.".encode("utf-8"))
        return

    headers, response = ({}, "")
    for k, v in RESPONSES.items():
        if prompt.startswith(k):
            headers, response = v
            break
    else:  # If no matches found
        self.send_response(500)
        self.end_headers()
        self.wfile.write(("Unknown Prompt:\n%s" % prompt).encode("utf-8"))
        return

    # Send response code
    self.send_response(200)

    # Send headers
    for k, v in headers.items():
        self.send_header(k, v)
    self.end_headers()

    # Send response body
    self.wfile.write(json.dumps(response).encode("utf-8"))
    return


def extract_shortened_prompt(content, model):
    prompt = content.get("inputText", None) or content.get("prompt", None)
    prompt = "::".join((model, prompt))  # Prepend model name to prompt key to keep separate copies
    return prompt.lstrip().split("\n")[0]


class MockExternalBedrockServer(MockExternalHTTPServer):
    # To use this class in a test one needs to start and stop this server
    # before and after making requests to the test app that makes the external
    # calls.

    def __init__(self, handler=simple_get, port=None, *args, **kwargs):
        super(MockExternalBedrockServer, self).__init__(handler=handler, port=port, *args, **kwargs)


if __name__ == "__main__":
    with MockExternalBedrockServer() as server:
        print("MockExternalBedrockServer serving on port %s" % str(server.port))
        while True:
            pass  # Serve forever
