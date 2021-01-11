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

import sys
import asyncio
from collections import namedtuple
from aiohttp.test_utils import (AioHTTPTestCase,
        TestClient as _TestClient)

from _target_application import make_app
import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer, MockExternalHTTPServer)

_coverage_source = [
    'newrelic.hooks.framework_aiohttp',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (framework_aiohttp)',
        default_settings=_default_settings)


ServerInfo = namedtuple('ServerInfo', ('base_metric', 'url'))


class SimpleAiohttpApp(AioHTTPTestCase):

    def __init__(self, server_cls, middleware, *args, **kwargs):
        super(SimpleAiohttpApp, self).__init__(*args, **kwargs)
        self.server_cls = server_cls
        self.middleware = None
        if middleware:
            self.middleware = [middleware]

    def setUp(self):
        super(SimpleAiohttpApp, self).setUp()
        asyncio.set_event_loop(self.loop)

    def get_app(self, *args, **kwargs):
        return make_app(self.middleware, loop=self.loop)

    @asyncio.coroutine
    def _get_client(self, app_or_server):
        """Return a TestClient instance."""
        client_constructor_arg = app_or_server

        scheme = 'http'
        host = '127.0.0.1'
        server_kwargs = {}
        if self.server_cls:
            test_server = self.server_cls(app_or_server, scheme=scheme,
                    host=host, **server_kwargs)
            client_constructor_arg = test_server

        try:
            return _TestClient(client_constructor_arg,
                    loop=self.loop)
        except TypeError:
            return _TestClient(client_constructor_arg)

    get_client = _get_client


@pytest.fixture()
def aiohttp_app(request):
    try:
        middleware = request.getfixturevalue('middleware')
    except:
        middleware = None
    try:
        server_cls = request.getfixturevalue('server_cls')
    except:
        server_cls = None
    case = SimpleAiohttpApp(server_cls=server_cls, middleware=middleware)
    case.setUp()
    yield case
    case.tearDown()


@pytest.fixture(scope='session')
def mock_header_server():
    def handler(self):
        if self.command != 'GET':
            self.send_response(501)
            self.end_headers()
            return

        response = str(self.headers).encode('utf-8')
        self.send_response(200)
        self.end_headers()
        self.wfile.write(response)

    with MockExternalHTTPHResponseHeadersServer(handler=handler) as _server:
        yield _server

@pytest.fixture(scope="session")
def mock_external_http_server():    
    response_values = []

    def respond_with_cat_header(self):
        headers, response_code = response_values.pop()
        self.send_response(response_code)
        for header, value in headers:
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(b'')

    with MockExternalHTTPServer(handler=respond_with_cat_header) as server:
        yield (server, response_values)


@pytest.fixture(scope='session')
def local_server_info(mock_header_server):
    host_port = '127.0.0.1:%d' % mock_header_server.port
    metric = 'External/%s/aiohttp/' % host_port
    url = 'http://' + host_port
    return ServerInfo(metric, url)
