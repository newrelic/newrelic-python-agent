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

import newrelic.packages.urllib3 as urllib3

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from newrelic.common.agent_http import BaseClient


def create_client_cls(status, data, url=None):
    if url:
        expected = urllib3.util.parse_url(url)
        if expected.port:
            expected_port = expected.port
        elif expected.scheme == 'https':
            expected_port = 443
        elif expected.scheme == 'http':
            expected_port = 80
        else:
            assert False, "Expected URL is missing scheme and port"
    else:
        expected = None

    class MockHttpClient(BaseClient):
        FAIL = False

        def __init__(self, host, port=80, *args, **kwargs):
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
            if expected:
                try:
                    assert self.host == expected.host
                    assert self.port == expected_port
                    assert path == expected.path
                    if expected.query:
                        query = urlencode(params)
                        assert query == expected.query
                except:
                    MockHttpClient.FAIL = True

            if status == 0:
                raise Exception

            return status, data

    return MockHttpClient
