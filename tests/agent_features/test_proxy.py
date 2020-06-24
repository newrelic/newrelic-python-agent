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

import pytest
# FIXME: urllib3
requests = pytest.importorskip('newrelic.packages.requests')
from newrelic.core.data_collector import _requests_request_url_workaround
from testing_support.mock_external_http_server import (
    MockExternalHTTPHResponseHeadersServer)

import pytest

# regression on a bug in the _requests_request_url_workaround patch from
# newrelic.core.data_collector.
@pytest.mark.parametrize('use_proxy', [False, True])
def test_envproxy(use_proxy, monkeypatch):

    # A simple mock server to echo back the request's request line.
    #
    # The http request line is what is sent before the headers, and has a form
    # of "method request-url http-protocol-version". for example, to request
    # from the root, we would send "GET / HTTP/1.1".
    #
    # however, when a proxy is configured, the request-url must be in the form
    # of an absolute path, i.e. "http://127.0.0.1:8989/" instead of "/". note
    # that this should only be the case when we're actually *using* this proxy.
    # so, if, for example, we're configuring a proxy on the nonexistant
    # "dummy://" protocol then we shouldn't be using the absolute uri in the
    # request-line

    def echo_requestline(self):
        response = str(self.requestline).encode('utf-8')
        self.send_response(200)
        self.end_headers()
        self.wfile.write(response)

    if use_proxy:
        monkeypatch.setenv("dummy_proxy", "meow")

    with MockExternalHTTPHResponseHeadersServer(handler=echo_requestline) as dummy_server:
        url = 'http://127.0.0.1:%d' % dummy_server.port

        resp = requests.get(url)
        assert url not in resp.text
