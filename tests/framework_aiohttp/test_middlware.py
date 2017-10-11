import pytest
import asyncio
import aiohttp

from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        override_generic_settings)


@asyncio.coroutine
def middleware_factory(app, handler):

    @asyncio.coroutine
    def middleware_handler(request):
        response = yield from handler(request)
        return response

    return middleware_handler


@pytest.mark.parametrize('nr_enabled', [True, False])
@pytest.mark.parametrize('middleware', [middleware_factory])
def test_middlware(nr_enabled, aiohttp_app, middleware):

    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request('GET', '/coro')
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text
        return resp

    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    if nr_enabled:
        scoped_metrics = [
            ('Function/_target_application:index', 1),
            ('Function/test_middlware:middleware_factory.'
                    '<locals>.middleware_handler', 1),
        ]

        rollup_metrics = [
            ('Function/_target_application:index', 1),
            ('Function/test_middlware:middleware_factory.'
                    '<locals>.middleware_handler', 1),
            ('Python/Framework/aiohttp/%s' % aiohttp.__version__, 1),
        ]

        _test = validate_transaction_metrics('_target_application:index',
                scoped_metrics=scoped_metrics,
                rollup_metrics=rollup_metrics)(_test)
    else:
        settings = global_settings()

        _test = override_generic_settings(settings, {'enabled': False})(_test)

    _test()
