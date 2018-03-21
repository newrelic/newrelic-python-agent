from newrelic.core.data_collector import _requests_request_url_workaround
from testing_support.mock_external_http_server import (
    MockExternalHTTPHResponseHeadersServer)
from newrelic.packages import requests

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
        assert (url in resp.text) is False