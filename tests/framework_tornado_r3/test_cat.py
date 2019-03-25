import json
import pytest
import sys
import webtest

try:
    import asyncio
except ImportError:
    asyncio = None

from newrelic.api.wsgi_application import wsgi_application
from newrelic.common.encoding_utils import deobfuscate

from testing_support.fixtures import (make_cross_agent_headers,
        override_application_settings)
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)
from tornado_base_test import (TornadoBaseTest, TornadoZmqBaseTest,
        TornadoAsyncIOBaseTest)
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

_override_settings_browser_enabled = dict(_override_settings)
_override_settings_browser_enabled['browser_monitoring.enabled'] = True

payload = ['b854df4feb2b1f06', False, '7e249074f277923d', '5d2957be']


@wsgi_application()
def _wsgi_app(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-Type', 'text/html; charset=UTF-8'), ]
    start_response(status, response_headers)
    return [b'Hello World']


wsgi_app = webtest.TestApp(_wsgi_app)


class AllTests(object):

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    def _test_cat_response(self):
        headers = make_cross_agent_headers(payload, ENCODING_KEY, '1#1')
        response = self.fetch_response('/', headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, HelloRequestHandler.RESPONSE)

        # Copy the headers into a regular dict, so we can check
        # case-sensitive header name. Otherwise, HTTPHeaders will
        # normalize the header name before comparing.

        tornado_response_headers = dict(**response.headers)

        # When this test was written, both tornado and wsgi use the same code
        # paths to generate the CAT response headers. It's conceivable that in
        # the future, tornado might use a different codepath from WSGI
        # applications. This test checks that WSGI and Tornado, at least to a
        # first order, are generating the same outputs.
        wsgi_response = wsgi_app.get('/', headers=headers)
        self.assertEqual(wsgi_response.status, '200 OK')

        self.assertTrue('X-NewRelic-App-Data' in tornado_response_headers)
        self.assertTrue('X-NewRelic-App-Data' in wsgi_response.headers)

        tornado_cat_data = json.loads(deobfuscate(
                tornado_response_headers['X-NewRelic-App-Data'], ENCODING_KEY))
        wsgi_cat_data = json.loads(deobfuscate(
                wsgi_response.headers['X-NewRelic-App-Data'], ENCODING_KEY))

        self.assertEqual(tornado_cat_data[0], '1#1')
        self.assertEqual(wsgi_cat_data[0], '1#1')

    @override_application_settings(_override_settings)
    def test_cat_response(self):
        self._test_cat_response()

    @override_application_settings(_override_settings_browser_enabled)
    def test_cat_response_browser_enabled(self):
        self._test_cat_response()

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @override_application_settings(_override_settings)
    def _test_external_cat_headers(self, url, req_type):
        with MockExternalHTTPHResponseHeadersServer() as external:
            headers = make_cross_agent_headers(payload, ENCODING_KEY, '1#1')
            response = self.fetch_response(
                    '/%s/%s/%s' % (url, req_type, external.port),
                    headers=headers)

        expected_request_headers = [b'Host', b'X-NewRelic-ID',
                b'X-NewRelic-Transaction']
        unexpected_response_header = b'X-NewRelic-App-Data'.lower()
        sent_headers = response.body

        self.assertEqual(response.code, 200)
        for expected_request_header in expected_request_headers:
            self.assertTrue(expected_request_header in sent_headers)
        self.assertTrue(unexpected_response_header not in sent_headers)

    def test_async_httpclient_req_obj_cat_headers(self):
        self._test_external_cat_headers('async-fetch', 'requestobj')

    def test_curl_async_httpclient_req_obj_cat_headers(self):
        self._test_external_cat_headers('curl-async-fetch', 'requestobj')

    def test_sync_httpclient_req_obj_cat_headers(self):
        self._test_external_cat_headers('sync-fetch', 'requestobj')

    def test_async_httpclient_url_cat_headers(self):
        self._test_external_cat_headers('async-fetch', 'url')

    def test_curl_async_httpclient_url_cat_headers(self):
        self._test_external_cat_headers('curl-async-fetch', 'url')

    def test_sync_httpclient_url_cat_headers(self):
        self._test_external_cat_headers('sync-fetch', 'url')


class TornadoPollIOLoopTest(AllTests, TornadoBaseTest):
    pass


@pytest.mark.skipif(sys.version_info < (2, 7),
        reason='pyzmq does not support Python 2.6')
class TornadoZmqIOLoopTest(AllTests, TornadoZmqBaseTest):
    pass


@pytest.mark.skipif(not asyncio, reason='No asyncio module available')
class TornadoAsyncIOLoopTest(AllTests, TornadoAsyncIOBaseTest):
    @pytest.mark.skip(
            reason='asyncio event loop does not support synchronous calls')
    def test_sync_httpclient_req_obj_cat_headers(self):
        pass

    @pytest.mark.skip(
            reason='asyncio event loop does not support synchronous calls')
    def test_sync_httpclient_url_cat_headers(self):
                pass
