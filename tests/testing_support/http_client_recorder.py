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

from collections import namedtuple

from newrelic.common.agent_http import DeveloperModeClient
from newrelic.common.encoding_utils import json_encode

Request = namedtuple("Request", ("method", "path", "params", "headers", "payload"))


class HttpClientRecorder(DeveloperModeClient):
    SENT = []
    STATUS_CODE = None
    STATE = 0

    def send_request(
        self, method="POST", path="/agent_listener/invoke_raw_method", params=None, headers=None, payload=None
    ):
        request = Request(method=method, path=path, params=params, headers=headers, payload=payload)
        self.SENT.append(request)
        if self.STATUS_CODE:
            # Define behavior for a 200 status code for use in test_agent_control_health.py
            if self.STATUS_CODE == 200:
                payload = {"return_value": "Hello World!"}
                response_data = json_encode(payload).encode("utf-8")
                return self.STATUS_CODE, response_data
            return self.STATUS_CODE, b""

        return super(HttpClientRecorder, self).send_request(method, path, params, headers, payload)

    def __enter__(self):
        HttpClientRecorder.STATE += 1

    def __exit__(self, exc, value, tb):
        HttpClientRecorder.STATE -= 1

    def close_connection(self):
        HttpClientRecorder.STATE -= 1
