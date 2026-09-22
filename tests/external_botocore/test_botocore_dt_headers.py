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

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import botocore.session
import pytest
from botocore.config import Config
from testing_support.fixtures import dt_enabled

from newrelic.api.background_task import background_task

AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"
AWS_REGION = "us-east-1"


class RecordingHandler(BaseHTTPRequestHandler):
    captured = []

    def _handle(self):
        # self.headers is an email.message.Message, which keeps repeated headers.
        RecordingHandler.captured.append(self.headers)
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "application/x-amz-json-1.0")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    do_GET = do_POST = _handle

    def log_message(self, *args, **kwargs):
        pass


@pytest.fixture
def endpoint_url():
    RecordingHandler.captured = []
    server = HTTPServer(("127.0.0.1", 0), RecordingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _client(service, endpoint_url):
    return botocore.session.get_session().create_client(
        service,
        region_name=AWS_REGION,
        endpoint_url=endpoint_url,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        # Path-style keeps the bucket out of the Host header so 127.0.0.1 resolves.
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 1}),
    )


def test_dt_headers_sent_once(endpoint_url):
    # The botocore hook adds DT headers before SigV4 signing, so they are
    # signed. A second copy added at send time makes AWS reject the signature.
    @dt_enabled
    @background_task()
    def _test():
        try:
            _client("s3", endpoint_url).get_object(Bucket="test-bucket", Key="test-key")
        except Exception:
            pass
        _client("dynamodb", endpoint_url).list_tables()

    _test()

    assert len(RecordingHandler.captured) == 2
    for headers in RecordingHandler.captured:
        signed_headers = headers["Authorization"].split("SignedHeaders=")[1].split(",")[0].split(";")
        for name in ("traceparent", "tracestate"):
            assert name in signed_headers
            assert len(headers.get_all(name) or []) == 1, headers.get_all(name)
