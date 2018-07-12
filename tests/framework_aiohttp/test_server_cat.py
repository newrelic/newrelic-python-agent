import asyncio
import json
import pytest

from newrelic.common.encoding_utils import deobfuscate
from testing_support.fixtures import (override_application_settings,
        make_cross_agent_headers, validate_analytics_catmap_data)

ENCODING_KEY = '1234567890123456789012345678901234567890'


@pytest.mark.parametrize(
    'inbound_payload,expected_intrinsics,forgone_intrinsics,cat_id', [

    # Valid payload from trusted account
    (["b854df4feb2b1f06", False, "7e249074f277923d", "5d2957be"],
    {"nr.referringTransactionGuid": "b854df4feb2b1f06",
    "nr.tripId": "7e249074f277923d",
    "nr.referringPathHash": "5d2957be"},
    [],
    '1#1'),

    # Valid payload from an untrusted account
    (["b854df4feb2b1f06", False, "7e249074f277923d", "5d2957be"],
    {},
    ['nr.referringTransactionGuid', 'nr.tripId', 'nr.referringPathHash'],
    '80#1'),
])
@pytest.mark.parametrize('method', ['GET'])
@pytest.mark.parametrize('uri,metric_name', [
    ('/error?hello=world', '_target_application:error'),
    ('/coro?hello=world', '_target_application:index'),
    ('/class?hello=world', '_target_application:HelloWorldView'),
])
def test_cat_headers(method, uri, metric_name, inbound_payload,
        expected_intrinsics, forgone_intrinsics, cat_id, aiohttp_app):

    @asyncio.coroutine
    def fetch():
        headers = make_cross_agent_headers(inbound_payload, ENCODING_KEY,
                cat_id)
        resp = yield from aiohttp_app.client.request(method, uri,
                headers=headers)

        try:
            resp_headers = dict(resp._nr_cat_header)
        except TypeError:
            resp_headers = dict(resp.headers)

        if expected_intrinsics:
            # test valid CAT response header
            assert 'X-NewRelic-App-Data' in resp_headers

            app_data = json.loads(deobfuscate(
                    resp_headers['X-NewRelic-App-Data'], ENCODING_KEY))
            assert app_data[0] == cat_id
            assert app_data[1] == ('WebTransaction/Function/%s' % metric_name)
        else:
            assert 'X-NewRelic-App-Data' not in resp_headers

    _custom_settings = {
            'cross_process_id': '1#1',
            'encoding_key': ENCODING_KEY,
            'trusted_account_ids': [1],
            'cross_application_tracer.enabled': True,
            'distributed_tracing.enabled': False,
    }

    @validate_analytics_catmap_data('WebTransaction/Function/%s' % metric_name,
            expected_attributes=expected_intrinsics,
            non_expected_attributes=forgone_intrinsics)
    @override_application_settings(_custom_settings)
    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    _test()
