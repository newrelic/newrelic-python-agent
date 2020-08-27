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

import asyncio
from enum import Enum


class ResponseState(Enum):
    NOT_STARTED = 1
    BODY = 2
    DONE = 3


class Response(object):
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = b"".join(body)


class AsgiTest(object):
    def __init__(self, asgi_application):
        self.asgi_application = asgi_application

    def make_request(self, method, path, params=None, headers=None, body=None):
        loop = asyncio.get_event_loop()
        coro = self.make_request_async(method, path, params, headers, body)
        return loop.run_until_complete(coro)

    def get(self, path, params=None, headers=None, body=None):
        return self.make_request("GET", path, params, headers, body)

    async def make_request_async(self, method, path, params, headers, body):
        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self.response_state = ResponseState.NOT_STARTED

        scope = self.generate_input(method, path, params, headers, body)

        try:
            awaitable = self.asgi_application(
                scope, self.input_queue.get, self.output_queue.put
            )
        except TypeError:
            instance = self.asgi_application(scope)
            awaitable = instance(self.input_queue.get, self.output_queue.put)

        await awaitable
        return self.process_output()

    def generate_input(self, method, path, params, headers, body):
        headers_list = []
        if headers:
            try:
                iterable = headers.items()
            except AttributeError:
                iterable = iter(headers)

            for key, value in iterable:
                header_tuple = (key.lower().encode("utf-8"), value.encode("utf-8"))
                headers_list.append(header_tuple)
        if not params:
            path, _, params = path.partition("?")

        scope = {
            "asgi": {"spec_version": "2.1", "version": "3.0"},
            "client": ("127.0.0.1", 54768),
            "headers": headers_list,
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
            "query_string": params and params.encode("utf-8") or b"",
            "raw_path": path.encode("utf-8"),
            "root_path": "",
            "scheme": "http",
            "server": ("127.0.0.1", 8000),
            "type": "http",
        }
        message = {"type": "http.request"}
        if body:
            message["body"] = body.encode("utf-8")

        self.input_queue.put_nowait(message)
        return scope

    def process_output(self):
        response_status = None
        response_headers = []
        body = []

        while True:
            try:
                message = self.output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            if self.response_state is ResponseState.NOT_STARTED:
                assert message["type"] == "http.response.start"
                response_status = message["status"]
                response_headers = message.get("headers", response_headers)
                self.response_state = ResponseState.BODY
            elif self.response_state is ResponseState.BODY:
                assert message["type"] == "http.response.body"
                body.append(message.get("body", b""))

                more_body = message.get("more_body", False)
                if not more_body:
                    self.response_state = ResponseState.DONE
            else:
                assert False, "ASGI protocol error: unexpected message"

        assert (
            self.response_state is ResponseState.DONE
        ), "ASGI protocol error: state is not DONE, expected additional messages"
        final_headers = {k.decode("utf-8"): v.decode("utf-8") for k, v in response_headers}
        assert len(final_headers) == len(response_headers), "Duplicate header names are not supported"
        return Response(response_status, final_headers, body)
