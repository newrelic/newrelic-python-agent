import asyncio
import pytest
from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        override_generic_settings)


async def coro_for_test(loop):
    await asyncio.sleep(0.1, loop=loop)


class FakeRequest:
    path = '/coro_for_test'
    method = 'GET'
    headers = {}
    content_type = 'Foobar'
    query_string = ''


@pytest.mark.parametrize('nr_enabled', [True, False])
def test_await(nr_enabled):
    from newrelic.hooks.framework_aiohttp import NRTransactionCoroutineWrapper

    async def _test_driver(loop):
        coro = coro_for_test(loop)

        # wrap the coroutine
        coro = NRTransactionCoroutineWrapper(coro, FakeRequest())

        return await coro

    loop = asyncio.new_event_loop()

    def _test():
        loop.run_until_complete(_test_driver(loop))

    if nr_enabled:
        _test = validate_transaction_metrics(
                'coro_for_test', group='Uri')(_test)
    else:
        settings = global_settings()
        _test = override_generic_settings(settings, {'enabled': False})(_test)

    _test()
