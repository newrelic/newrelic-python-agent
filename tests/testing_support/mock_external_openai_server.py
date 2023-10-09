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

RESPONSES = {
    "You are a scientist.": [
        {
            "Content-Type": "application/json",
            "openai-model": "gpt-3.5-turbo-0613",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "1090",
            "openai-version": "2020-10-01",
            "x-request-id": "efe27ad067ad8c6a551f0338ad7b4ca3",
        },
        {
            "id": "chatcmpl-85dpg8pZBkSu7nDIoiyjOSChBQAT5",
            "object": "chat.completion",
            "created": 1696355448,
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "212 degrees Fahrenheit is equivalent to 100 degrees Celsius.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 53, "completion_tokens": 11, "total_tokens": 64},
        },
    ],
    "This is an embedding test.": [
        {
            "Content-Type": "application/json",
            "openai-organization": "new-relic-nkmd8b",
            "openai-processing-ms": "19",
            "openai-version": "2020-10-01",
            "x-request-id": "54367a09303968f98cf1941adcd00c5a",
        },
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
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        },
    ],
}


def simple_get(self):
    content_len = int(self.headers.get("content-length"))
    content = json.loads(self.rfile.read(content_len).decode("utf-8"))

    prompt = extract_shortened_prompt(content)
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


def extract_shortened_prompt(content):
    prompt = (
        content.get("prompt", None)
        or content.get("input", None)
        or "\n".join(m["content"] for m in content.get("messages"))
    )
    return prompt.lstrip().split("\n")[0]


class MockExternalOpenAIServer(MockExternalHTTPServer):
    # To use this class in a test one needs to start and stop this server
    # before and after making requests to the test app that makes the external
    # calls.

    def __init__(self, handler=simple_get, port=None, *args, **kwargs):
        super(MockExternalOpenAIServer, self).__init__(handler=handler, port=port, *args, **kwargs)


if __name__ == "__main__":
    with MockExternalOpenAIServer() as server:
        print("MockExternalOpenAIServer serving on port %s" % str(server.port))
        while True:
            pass  # Serve forever
