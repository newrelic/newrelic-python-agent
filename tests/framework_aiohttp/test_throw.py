import pytest
import asyncio
from aiohttp.test_utils import AioHTTPTestCase
from _target_application import make_app, load_flame_thrower

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors)


class SimpleAiohttpApp(AioHTTPTestCase):

    def get_app(self):
        return make_app([load_flame_thrower])


@pytest.fixture(autouse=True)
def aiohttp_app():
    case = SimpleAiohttpApp()
    case.setUp()
    yield case
    case.tearDown()


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
])
def test_exception_raised(method, uri, metric_name, expect100, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(
                method, uri, expect100=expect100)
        assert resp.status == 500

    @validate_transaction_metrics(metric_name)
    @validate_transaction_errors(errors=['_target_application:KnownException'])
    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    _test()


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
    ('/known_error', '_target_application:KnownErrorView'),
])
def test_exception_ignored(method, uri, metric_name, expect100, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(
                method, uri, expect100=expect100)
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(metric_name)
    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    _test()


@pytest.mark.parametrize('method', [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
])
def test_error_exception(method, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(method, '/error')
        assert resp.status == 500

    @validate_transaction_errors(errors=['builtins:ValueError'])
    @validate_transaction_metrics('_target_application:error')
    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    _test()
