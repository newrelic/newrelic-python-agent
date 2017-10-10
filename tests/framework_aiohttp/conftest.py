import asyncio
from aiohttp.test_utils import (AioHTTPTestCase,
        TestClient as _TestClient)
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


class SimpleAiohttpApp(AioHTTPTestCase):

    def __init__(self, server_cls, middleware, *args, **kwargs):
        super(SimpleAiohttpApp, self).__init__(*args, **kwargs)
        self.server_cls = server_cls
        self.middleware = None
        if middleware:
            self.middleware = [middleware]

    def get_app(self):
        return make_app(self.middleware)

    @asyncio.coroutine
    def _get_client(self, app):
        """Return a TestClient instance."""
        if self.server_cls:
            scheme = "http"
            host = '127.0.0.1'
            server_kwargs = {}
            test_server = self.server_cls(
                    app,
                    scheme=scheme, host=host, **server_kwargs)
            return _TestClient(test_server, loop=self.loop)
        else:
            client = yield from super(SimpleAiohttpApp, self)._get_client(app)
            return client


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
