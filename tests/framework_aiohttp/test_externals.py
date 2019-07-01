import pytest
import asyncio

from testing_support.fixtures import (validate_transaction_metrics,
        validate_tt_parenting)

expected_parenting = (
    'TransactionNode', [
        ('FunctionNode', [
            ('ExternalTrace', []),
            ('ExternalTrace', []),
        ]),
])


@validate_tt_parenting(expected_parenting)
@validate_transaction_metrics('_target_application:multi_fetch_handler',
        rollup_metrics=[('External/all', 2)])
def test_multiple_requests_within_transaction(local_server_info, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request('GET', '/multi_fetch',
                params={'url': local_server_info.url})
        assert resp.status == 200

    aiohttp_app.loop.run_until_complete(fetch())
