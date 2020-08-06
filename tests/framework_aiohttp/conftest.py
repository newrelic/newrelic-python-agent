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
        MockExternalHTTPHResponseHeadersServer)

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


@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration):
    pass


@pytest.fixture(scope='function')
def requires_data_collector(collector_available_fixture):
    pass


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


@pytest.fixture(scope='module')
def external():
    external = MockExternalHTTPHResponseHeadersServer()
    with external:
        yield external


@pytest.fixture(scope='module')
def local_server_info(external):
    host_port = '127.0.0.1:%d' % external.port
    metric = 'External/%s/aiohttp/' % host_port
    url = 'http://' + host_port
    return ServerInfo(metric, url)
