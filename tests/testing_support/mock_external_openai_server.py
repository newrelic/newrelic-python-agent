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
import threading

from newrelic.packages.six.moves import BaseHTTPServer
from testing_support.util import get_open_port


# This defines an external server test apps can make requests to (instead of
# www.google.com for example). This provides 3 features:
#
# 1) This removes dependencies on external websites.
# 2) Provides a better mechanism for making an external call in a test app than
#    simple calling another endpoint the test app makes available because this
#    server will not be instrumented meaning we don't have to sort through
#    transactions to separate the ones created in the test app and the ones
#    created by an external call.
# 3) This app runs on a separate thread meaning it won't block the test app.


def simple_get(self):
    content_len = int(self.headers.get('content-length'))
    content = json.loads(self.rfile.read(content_len).decode("utf-8"))

    if self.path == "/chat/completions":
        prompt = content["prompt"].strip()
        response, headers = ({}, "")
        for k, v in MockExternalOpenAIServer.RESPONSES.items():
            if prompt.startswith(k):
                response, headers = v
                break
        else:  # If no matches found
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Unknown Prompt")

        # Send response code
        self.send_response(200)

        # Send headers
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()

        # Send response body
        self.wfile.write(json.dumps(response).encode("utf-8"))
    else:
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Unknown Path")


class MockExternalOpenAIServer(threading.Thread):
    # To use this class in a test one needs to start and stop this server
    # before and after making requests to the test app that makes the external
    # calls.
    RESPONSES = {
        "Suggest three names for an animal": ({}, {
            "warning": "This model version is deprecated. Migrate before January 4, 2024 to avoid disruption of service. Learn more https://platform.openai.com/docs/deprecations",
            "id": "cmpl-85KiuTDTtg3pAKWyMHWcN6OEUZskB",
            "object": "text_completion",
            "created": 1696281992,
            "model": "text-davinci-003",
            "choices": [
                {
                    "text": " Thunderbun, Thumper Man, Daredevil Hare",
                    "index": 0,
                    "logprobs": "None",
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 61, "completion_tokens": 10, "total_tokens": 71},
        })
    }

    def __init__(self, port=None, *args, **kwargs):
        super(MockExternalOpenAIServer, self).__init__(*args, **kwargs)
        self.daemon = True
        handler = type(
            "ResponseHandler",
            (
                BaseHTTPServer.BaseHTTPRequestHandler,
                object,
            ),
            {
                "do_GET": simple_get,
                "do_OPTIONS": simple_get,
                "do_HEAD": simple_get,
                "do_POST": simple_get,
                "do_PUT": simple_get,
                "do_PATCH": simple_get,
                "do_DELETE": simple_get,
            },
        )

        if port:
            self.httpd = BaseHTTPServer.HTTPServer(("localhost", port), handler)
            self.port = port
        else:
            # If port not set, try to bind to a port until successful
            retries = 5  # Set retry limit to prevent infinite loops
            self.port = None  # Initialize empty
            while not self.port and retries > 0:
                retries -= 1
                try:
                    # Obtain random open port
                    port = get_open_port()
                    # Attempt to bind to port
                    self.httpd = BaseHTTPServer.HTTPServer(("localhost", port), handler)
                    self.port = port
                except OSError as exc:
                    # Reraise errors other than port already in use
                    if "Address already in use" not in exc:
                        raise

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, tb):
        self.stop()

    def run(self):
        self.httpd.serve_forever()

    def stop(self):
        # Shutdowns the httpd server.
        self.httpd.shutdown()
        # Close the socket so we can reuse it.
        self.httpd.socket.close()
        self.join()


if __name__ == "__main__":
    with MockExternalOpenAIServer() as server:
        print("MockExternalOpenAIServer serving on port %s" % str(server.port))
        while True: pass  # Server forever
