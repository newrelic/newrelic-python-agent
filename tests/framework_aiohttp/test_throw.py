import pytest
import asyncio
import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer as _TestServer
from _target_application import KnownException
from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors, override_generic_settings)


class ThrowServer(_TestServer):
    @asyncio.coroutine
    def _make_factory(self, **kwargs):
        server = yield from super(ThrowServer, self)._make_factory(
                **kwargs)

        handler = server.request_handler

        @asyncio.coroutine
        def coro_throws(request):
            # start handler call
            coro = handler(request)
            if hasattr(coro, '__iter__'):
                coro = iter(coro)
            try:
                while True:
                    yield
                    next(coro)
                    coro.throw(KnownException)
            except StopIteration as e:
                return e.value
            except Exception as e:
                return web.Response(status=500, text=str(e))

        server.request_handler = coro_throws

        return server


@pytest.mark.parametrize('server_cls', [ThrowServer])
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
])
def test_exception_raised(method, uri, metric_name, error, expect100,
        nr_enabled, server_cls, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(
                method, uri, expect100=expect100)
        assert resp.status == 500

    if nr_enabled:
        @validate_transaction_metrics(metric_name,
            scoped_metrics=[
                ('Function/%s' % metric_name, 1),
            ],
            rollup_metrics=[
                ('Function/%s' % metric_name, 1),
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


@pytest.mark.parametrize('server_cls', [ThrowServer])
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
        server_cls, aiohttp_app):
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
            scoped_metrics=[
                ('Function/%s' % metric_name, 1),
            ],
            rollup_metrics=[
                ('Function/%s' % metric_name, 1),
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
