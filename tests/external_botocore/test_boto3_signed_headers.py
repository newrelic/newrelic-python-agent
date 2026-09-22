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

import boto3
import pytest
from botocore.config import Config
from testing_support.fixtures import dt_enabled, override_application_settings
from testing_support.mock_external_http_server import MockExternalHTTPServer

from newrelic.api.background_task import background_task
from newrelic.hooks.external_botocore import NEWRELIC_SIGNED_HEADERS_DENYLIST

AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"
AWS_REGION_NAME = "us-west-2"

LIST_BUCKETS_RESPONSE = b"""<?xml version="1.0" encoding="UTF-8"?>
<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Owner><ID>test-owner-id</ID><DisplayName>test-owner</DisplayName></Owner>
    <Buckets/>
</ListAllMyBucketsResult>"""


def handler(captured_headers):
    def _handler(self):
        captured_headers.append(dict(self.headers))
        self.send_response(200)
        self.send_header("Content-Type", "application/xml")
        self.end_headers()
        self.wfile.write(LIST_BUCKETS_RESPONSE)

    return _handler


@pytest.fixture
def mock_server():
    captured_headers = []
    with MockExternalHTTPServer(handler=handler(captured_headers)) as server:
        server._captured_headers = captured_headers
        yield server


@pytest.mark.parametrize("exclude_newrelic_header", (True, False))
def test_header_signing_excludes_dt_headers(exclude_newrelic_header, mock_server):
    @dt_enabled
    @override_application_settings({"distributed_tracing.exclude_newrelic_header": exclude_newrelic_header})
    @background_task(name="test_header_signing_excludes_dt_headers")
    def _test():
        captured_headers = mock_server._captured_headers
        client = boto3.client(
            "s3",
            endpoint_url=f"http://localhost:{mock_server.port}",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME,
            config=Config(signature_version="s3v4"),
        )
        resp = client.list_buckets()
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        # We should only have caught headers from 1 request
        assert len(captured_headers) == 1
        captured_headers = {k.lower(): v for k, v in captured_headers[0].items()}

        # Ensure we actually did inject DT headers
        assert "traceparent" in captured_headers
        assert "tracestate" in captured_headers
        assert ("newrelic" not in captured_headers) == exclude_newrelic_header

        # Extract the signed headers portion of the authorization header value
        authorization = captured_headers["authorization"]
        signed_headers = set(authorization.split("SignedHeaders=", 1)[1].split(",", 1)[0].split(";"))

        # Sanity check to ensure we actually extracted the signed headers list
        assert "host" in signed_headers

        # Verify the DT headers did NOT get signed
        blacklisted = {h.lower() for h in NEWRELIC_SIGNED_HEADERS_DENYLIST}
        assert not (signed_headers & blacklisted)

    _test()
