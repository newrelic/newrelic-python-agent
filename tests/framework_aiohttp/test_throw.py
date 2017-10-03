import pytest
import asyncio
import aiohttp
from aiohttp.test_utils import AioHTTPTestCase
from _target_application import make_app, load_coro_throws
from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors, override_generic_settings)


class SimpleAiohttpApp(AioHTTPTestCase):

    def get_app(self):
        return make_app([load_coro_throws])


@pytest.fixture(autouse=True)
def aiohttp_app():
    case = SimpleAiohttpApp()
    case.setUp()
    yield case
    case.tearDown()


@pytest.mark.parametrize('nr_enabled', [True, False])
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
@pytest.mark.parametrize('uri,metric_name,error', [
    ('/coro', '_target_application:index',
            '_target_application:KnownException'),
    ('/class', '_target_application:HelloWorldView',
            '_target_application:KnownException'),
    ('/error', '_target_application:error',
            'builtins:ValueError'),
])
def test_exception_raised(method, uri, metric_name, error, expect100,
        nr_enabled, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(
                method, uri, expect100=expect100)
        assert resp.status == 500

    if nr_enabled:
        @validate_transaction_metrics(metric_name,
            rollup_metrics=[
                ('Python/Framework/aiohttp/%s' % aiohttp.__version__, 1),
            ],
        )
        @validate_transaction_errors(errors=[error])
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())
    else:
        settings = global_settings()

        @override_generic_settings(settings, {'enabled': False})
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())

    _test()


@pytest.mark.parametrize('nr_enabled', [True, False])
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
def test_exception_ignored(method, uri, metric_name, expect100, nr_enabled,
        aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(
                method, uri, expect100=expect100)
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text

    if nr_enabled:
        @validate_transaction_errors(errors=[])
        @validate_transaction_metrics(metric_name,
            rollup_metrics=[
                ('Python/Framework/aiohttp/%s' % aiohttp.__version__, 1),
            ],
        )
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())
    else:
        settings = global_settings()

        @override_generic_settings(settings, {'enabled': False})
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())

    _test()
