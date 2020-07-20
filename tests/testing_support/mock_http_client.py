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

import urllib3

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from newrelic.common.agent_http import BaseClient


class MockHttpClient(BaseClient):
    STATUS = 200
    DATA = None
    EXPECTED_URL = None
    FAIL = False

    def __init__(
            self,
            host,
            port=80,
            proxy_scheme=None,
            proxy_host=None,
            proxy_port=None,
            proxy_user=None,
            proxy_pass=None,
            timeout=None,
            ca_bundle_path=None,
            disable_certificate_validation=False,
            compression_threshold=64 * 1024,
            compression_level=None,
            compression_method="gzip",
            max_payload_size_in_bytes=1000000,
            audit_log_fp=None,
    ):
        self.host = host
        self.port = port

    def send_request(
            self,
            method="POST",
            path="/agent_listener/invoke_raw_method",
            params=None,
            headers=None,
            payload=None,
    ):
        if self.EXPECTED_URL:
            components = urllib3.util.parse_url(self.EXPECTED_URL)
            port = components.port or 80
            try:
                assert components.scheme == "http"
                assert components.host == self.host
                assert port == self.port
                assert components.path == path
                if params:
                    query = urlencode(params)
                    assert components.query == query
            except:
                MockHttpClient.FAIL = True

        if self.STATUS == 0:
            raise Exception
        return self.STATUS, self.DATA
