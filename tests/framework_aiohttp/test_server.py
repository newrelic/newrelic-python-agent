import pytest
import sys
import asyncio
from aiohttp.test_utils import AioHTTPTestCase
from _target_application import make_app, load_close_middleware
from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors, count_transactions,
        override_generic_settings)

middlewares = [None, load_close_middleware]
if sys.version_info >= (3, 5):
    from _middleware_await import load_coro_awaits
    middlewares.append(load_coro_awaits)


class SimpleAiohttpApp(AioHTTPTestCase):

    def __init__(self, middleware, *args, **kwargs):
        super(SimpleAiohttpApp, self).__init__(*args, **kwargs)
        self.middleware = None
        if middleware:
            self.middleware = [middleware]

    def get_app(self):
        return make_app(self.middleware)


@pytest.fixture(autouse=True)
def aiohttp_app(request):
    try:
        middleware = request.getfixturevalue('middleware')
    except:
        middleware = None
    case = SimpleAiohttpApp(middleware=middleware)
    case.setUp()
    yield case
    case.tearDown()


@pytest.mark.parametrize('nr_enabled', [True, False])
@pytest.mark.parametrize('middleware', middlewares)
@pytest.mark.parametrize('expect100', [
    True,
    False,
])
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
    ('/known_error', '_target_application:KnownErrorView'),
])
def test_valid_response(method, uri, metric_name, expect100, middleware,
        nr_enabled, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(
                method, uri, expect100=expect100)
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text

    if nr_enabled:
        @validate_transaction_metrics(metric_name)
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())
    else:
        settings = global_settings()

        @override_generic_settings(settings, {'enabled': False})
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())

    _test()


@pytest.mark.parametrize('nr_enabled', [True, False])
@pytest.mark.parametrize('middleware', middlewares)
@pytest.mark.parametrize('method', [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
])
def test_error_exception(method, middleware, nr_enabled, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(method, '/error')
        assert resp.status == 500

    if nr_enabled:
        @validate_transaction_errors(errors=['builtins:ValueError'])
        @validate_transaction_metrics('_target_application:error')
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())
    else:
        settings = global_settings()

        @override_generic_settings(settings, {'enabled': False})
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())

    _test()


@pytest.mark.parametrize('nr_enabled', [True, False])
@pytest.mark.parametrize('middleware', middlewares)
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
    ('/known_error', '_target_application:KnownErrorView'),
])
def test_simultaneous_requests(method, uri, metric_name, middleware,
        nr_enabled, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(method, uri)
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text
        return resp

    @asyncio.coroutine
    def multi_fetch(loop):
        coros = [fetch() for i in range(2)]
        combined = asyncio.gather(*coros, loop=loop)
        responses = yield from combined
        return responses

    if nr_enabled:
        transactions = []

        @validate_transaction_metrics(metric_name)
        @count_transactions(transactions)
        def _test():
            aiohttp_app.loop.run_until_complete(multi_fetch(aiohttp_app.loop))
            assert len(transactions) == 2
    else:
        settings = global_settings()

        @override_generic_settings(settings, {'enabled': False})
        def _test():
            aiohttp_app.loop.run_until_complete(multi_fetch(aiohttp_app.loop))

    _test()
