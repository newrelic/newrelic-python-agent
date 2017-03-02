import sys

import pytest

from testing_support.fixtures import (make_cross_agent_headers,
        override_application_settings)
from tornado_base_test import TornadoBaseTest, TornadoZmqBaseTest
from tornado_fixtures import (
        tornado_validate_errors, tornado_validate_transaction_cache_empty)

from _test_async_application import HelloRequestHandler

ENCODING_KEY = '1234567890123456789012345678901234567890'

_override_settings = {
    'cross_process_id': '1#1',
    'encoding_key': ENCODING_KEY,
    'trusted_account_ids': [1],
    'browser_monitoring.enabled': False,
}

payload = ['b854df4feb2b1f06', False, '7e249074f277923d', '5d2957be']


class AllTests(object):

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @override_application_settings(_override_settings)
    def test_cat_response(self):
        headers = make_cross_agent_headers(payload, ENCODING_KEY, '1#1')
        response = self.fetch_response('/', headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, HelloRequestHandler.RESPONSE)

        # Copy the headers into a regular dict, so we can check
        # case-sensitive header name. Otherwise, HTTPHeaders will
        # normalize the header name before comparing.

        headers = dict(**response.headers)

        # TODO: When we add ability to send "New Relic cased" headers,
        # then we need to test for `X-NewRelic-App-Data` (capital 'R').

        self.assertTrue('X-Newrelic-App-Data' in headers)


class TornadoDefaultIOLoopTest(AllTests, TornadoBaseTest):
    pass

@pytest.mark.skipif(sys.version_info < (2, 7),
        reason='pyzmq does not support Python 2.6')
class TornadoZmqIOLoopTest(AllTests, TornadoZmqBaseTest):
    pass
