from collections import namedtuple

from newrelic.common.agent_http import DeveloperModeClient
from newrelic.common.encoding_utils import json_encode

Request = namedtuple("Request", ("method", "path", "params", "headers", "payload"))

class HttpClientRecorder(DeveloperModeClient):
    SENT = []
    STATUS_CODE = None
    STATE = 0

    def send_request(
        self,
        method="POST",
        path="/agent_listener/invoke_raw_method",
        params=None,
        headers=None,
        payload=None,
    ):
        request = Request(method=method, path=path, params=params, headers=headers, payload=payload)
        self.SENT.append(request)
        if self.STATUS_CODE:
            # Define behavior for a 200 status code for use in test_super_agent_health.py
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
