import asyncio
import pytest

from testing_support.fixtures import (override_application_settings,
        make_cross_agent_headers, validate_analytics_catmap_data)

ENCODING_KEY = '1234567890123456789012345678901234567890'


@pytest.mark.parametrize(
    'inbound_payload,expected_intrinsics,forgone_intrinsics', [
    (["b854df4feb2b1f06", False, "7e249074f277923d", "5d2957be"],
    {"nr.referringTransactionGuid": "b854df4feb2b1f06",
    "nr.tripId": "7e249074f277923d",
    "nr.referringPathHash": "5d2957be"},
    []),
])
@pytest.mark.parametrize('method', ['GET'])
@pytest.mark.parametrize('uri,metric_name', [
    ('/coro?hello=world', '_target_application:index'),
    ('/class?hello=world', '_target_application:HelloWorldView'),
])
def test_inbound_cat_headers(method, uri, metric_name, inbound_payload,
        expected_intrinsics, forgone_intrinsics, aiohttp_app):

    @asyncio.coroutine
    def fetch():
        headers = make_cross_agent_headers(inbound_payload, ENCODING_KEY,
                '1#1')
        resp = yield from aiohttp_app.client.request(method, uri,
                headers=headers)
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text

    _custom_settings = {
            'cross_process_id': '1#1',
            'encoding_key': ENCODING_KEY,
            'trusted_account_ids': [1],
            'cross_application_tracer.enabled': True,
    }

    @validate_analytics_catmap_data('WebTransaction/Function/%s' % metric_name,
            expected_attributes=expected_intrinsics,
            non_expected_attributes=forgone_intrinsics)
    @override_application_settings(_custom_settings)
    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    _test()
