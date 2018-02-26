import pytest
import aiohttp
import asyncio

from testing_support.fixtures import validate_transaction_metrics

version_info = tuple(int(_) for _ in aiohttp.__version__.split('.')[:2])


@pytest.mark.xfail(version_info >= (3, 0), reason='aiohttp 3.x PYTHON-2674',
        strict=True)
@validate_transaction_metrics('_target_application:multi_fetch_handler',
        rollup_metrics=[('External/all', 2)])
def test_multiple_requests_within_transaction(aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request('GET', '/multi_fetch')
        assert resp.status == 200

    aiohttp_app.loop.run_until_complete(fetch())
