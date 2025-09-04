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

from testing_support.mock_external_http_server import MockExternalHTTPServer

RESPONSES = {
    "What is 212 degrees Fahrenheit converted to Celsius?": [
        {"Content-Type": "application/json", "x-amzn-RequestId": "c20d345e-6878-4778-b674-6b187bae8ecf"},
        200,
        {
            "metrics": {"latencyMs": 1866},
            "output": {
                "message": {
                    "content": [
                        {
                            "text": "To convert 212°F to Celsius, we can use the formula:\n\nC = (F - 32) x 5/9\n\nWhere:\nC is the temperature in Celsius\nF is the temperature in Fahrenheit\n\nPlugging in 212°F, we get:\n\nC = (212 - 32) x 5/9\nC = 180 x 5/9\nC = 100\n\nTherefore, 212°"
                        }
                    ],
                    "role": "assistant",
                }
            },
            "stopReason": "max_tokens",
            "usage": {"inputTokens": 26, "outputTokens": 100, "totalTokens": 126},
        },
    ],
    "Invalid Token": [
        {
            "Content-Type": "application/json",
            "x-amzn-RequestId": "e1206e19-2318-4a9d-be98-017c73f06118",
            "x-amzn-ErrorType": "UnrecognizedClientException:http://internal.amazon.com/coral/com.amazon.coral.service/",
        },
        403,
        {"message": "The security token included in the request is invalid."},
    ],
    "Model does not exist.": [
        {
            "Content-Type": "application/json",
            "x-amzn-RequestId": "f4908827-3db9-4742-9103-2bbc34578b03",
            "x-amzn-ErrorType": "ValidationException:http://internal.amazon.com/coral/com.amazon.bedrock/",
        },
        400,
        {"message": "The provided model identifier is invalid."},
    ],
}


def simple_get(self):
    content_len = int(self.headers.get("content-length"))
    body = self.rfile.read(content_len).decode("utf-8")
    try:
        content = json.loads(body)
    except Exception:
        content = body

    prompt = extract_shortened_prompt_converse(content)
    if not prompt:
        self.send_response(500)
        self.end_headers()
        self.wfile.write(b"Could not parse prompt.")
        return

    headers, status_code, response = ({}, 0, "")

    for k, v in RESPONSES.items():
        if prompt.startswith(k):
            headers, status_code, response = v
            break

    if not response:
        # If no matches found
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
    response_body = json.dumps(response).encode("utf-8")

    self.wfile.write(response_body)
    return


def extract_shortened_prompt_converse(content):
    try:
        prompt = content["messages"][0].get("content")[0].get("text", None)
        # Sometimes there are leading whitespaces in the prompt.
        prompt = prompt.lstrip().split("\n")[0]
    except Exception:
        prompt = ""
    return prompt


class MockExternalBedrockConverseServer(MockExternalHTTPServer):
    # To use this class in a test one needs to start and stop this server
    # before and after making requests to the test app that makes the external
    # calls.

    def __init__(self, handler=simple_get, port=None, *args, **kwargs):
        super().__init__(handler=handler, port=port, *args, **kwargs)  # noqa: B026
