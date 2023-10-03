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

ALLOWED_PATHS = set(["/chat/completions"])

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
    ]
}


def simple_get(self):
    content_len = int(self.headers.get("content-length"))
    content = json.loads(self.rfile.read(content_len).decode("utf-8"))
    if "prompt" in content:
        prompt = content["prompt"].strip()
    elif "messages" in content:
        print(content)
        prompt = "\n".join(m["content"].strip() for m in content["messages"])

    if self.path in ALLOWED_PATHS:
        print(prompt)
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
    else:
        self.send_response(404)
        self.end_headers()
        self.wfile.write(("Unknown Path: %s" % self.path).encode("utf-8"))
        return


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
