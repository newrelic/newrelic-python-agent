import asyncio
from aiohttp.test_utils import (AioHTTPTestCase,
        TestClient as _TestClient)
from aiohttp import ClientResponse

try:
    from aiohttp import HttpResponseParser
except ImportError:
    from aiohttp.http_parser import HttpResponseParser

from _target_application import make_app
import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)

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


@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration):
    pass


@pytest.fixture(scope='function')
def requires_data_collector(collector_available_fixture):
    pass


cat_headers = []


class HeaderResponseParser(HttpResponseParser):

    def parse_headers(self, lines):
        for line in lines:
            if line.startswith(b'X-NewRelic-App-Data:'):
                decoded = line.decode('utf-8')
                cat_header = tuple(decoded.split(': '))
                cat_headers.append([cat_header])

        return super(HeaderResponseParser, self).parse_headers(lines)


class RealHeadersResponse(ClientResponse):
    try:
        _response_parser = HeaderResponseParser()
    except TypeError:
        pass

    @asyncio.coroutine
    def start(self, *args, **kwargs):
        response = yield from super(RealHeadersResponse, self).start(*args,
                **kwargs)

        _nr_cat_header = None
        if cat_headers:
            _nr_cat_header = cat_headers.pop()
        response._nr_cat_header = _nr_cat_header

        return response


class SimpleAiohttpApp(AioHTTPTestCase):

    def __init__(self, server_cls, middleware, *args, **kwargs):
        super(SimpleAiohttpApp, self).__init__(*args, **kwargs)
        self.server_cls = server_cls
        self.middleware = None
        if middleware:
            self.middleware = [middleware]

    def get_app(self, *args, **kwargs):
        return make_app(self.middleware, loop=self.loop)

    @asyncio.coroutine
    def _get_client(self, app):
        """Return a TestClient instance."""
        client_constructor_arg = app

        scheme = "http"
        host = '127.0.0.1'
        server_kwargs = {}
        if self.server_cls:
            test_server = self.server_cls(
                    app,
                    scheme=scheme, host=host, **server_kwargs)
            client_constructor_arg = test_server

        try:
            return _TestClient(client_constructor_arg,
                    loop=self.loop,
                    response_class=RealHeadersResponse)
        except TypeError:
            return _TestClient(client_constructor_arg,
                    response_class=RealHeadersResponse)


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
