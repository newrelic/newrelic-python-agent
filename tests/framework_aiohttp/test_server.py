import pytest
import asyncio
from aiohttp.test_utils import AioHTTPTestCase
from _target_application import make_app

from testing_support.fixtures import validate_transaction_metrics


class SimpleAiohttpApp(AioHTTPTestCase):

    def get_app(self):
        return make_app()


@pytest.fixture(autouse=True)
def aiohttp_app():
    case = SimpleAiohttpApp()
    case.setUp()
    yield case
    case.tearDown()


@pytest.mark.parametrize('method', [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
])
@pytest.mark.parametrize('uri,metric_name', [
    ('/coro', '_target_application:index'),
    ('/class', '_target_application:HelloWorldView'),
])
def test_valid_response(method, uri, metric_name, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(method, uri)
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text

    @validate_transaction_metrics(metric_name)
    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    _test()
