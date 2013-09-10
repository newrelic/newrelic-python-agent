import unittest
import socket
import os
import json
import zlib

import mock

from newrelic.packages import six

from newrelic.network.platform_api import PlatformInterface, USER_AGENT
from newrelic.network.exceptions import (DiscardDataForRequest,
        RetryDataForRequest, ServerIsUnavailable)

from newrelic.packages import requests

class TestPlatformInterface(unittest.TestCase):

    @mock.patch('newrelic.packages.requests.session')
    @mock.patch('newrelic.network.platform_api.PlatformInterface.send_request')
    def test_platform_session(self, platform_interface_send_request_mock,
            requests_session_mock):

        requests_session_object = mock.MagicMock()

        requests_session_mock.return_value = requests_session_object
        platform_interface_send_request_mock.return_value = 200

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()
        session_instance.send_metric_data('NAME', 'GUID', 'VERSION', 123, ())

        (url, proxies, session, payload), kwargs = \
                platform_interface_send_request_mock.call_args

        self.assertEqual(url, 'http://HOST/platform/v1/metrics')
        self.assertEqual(proxies, None)
        self.assertEqual(session, requests_session_object)

        self.assertTrue(isinstance(payload, dict))

        agent = payload['agent']

        self.assertEqual(agent['version'], 'VERSION')
        self.assertEqual(agent['host'], socket.gethostname())
        self.assertEqual(agent['pid'], os.getpid())

        component = payload['components'][0]

        self.assertEqual(component['name'], 'NAME')
        self.assertEqual(component['guid'], 'GUID')
        self.assertEqual(component['duration'], 123)
        self.assertEqual(component['metrics'], ())

        session_instance.close_connection()

        self.assertTrue(requests_session_object.close.called)

    @mock.patch('newrelic.packages.requests.session')
    def test_outgoing_request(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=200, content='{"status":"RESULT"}')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()
        result = session_instance.send_metric_data(
                'NAME', 'GUID', 'VERSION', 123, ())

        self.assertEqual(result, 'RESULT')

        self.assertTrue(requests_session_object.post.called)

        (url,), kwargs = requests_session_object.post.call_args

        self.assertEqual(url, 'http://HOST/platform/v1/metrics')

        self.assertEqual(kwargs['proxies'], None)
        self.assertEqual(kwargs['timeout'], 30.0)

        headers = dict(kwargs['headers'])

        self.assertEqual(headers.get('User-Agent'), USER_AGENT)
        self.assertEqual(headers.get('Content-Encoding'), 'identity')
        self.assertEqual(headers.get('X-License-Key'), 'LICENSE-KEY')

        payload = json.loads(kwargs['data'])

        agent = payload['agent']

        self.assertEqual(agent['version'], 'VERSION')
        self.assertEqual(agent['host'], socket.gethostname())
        self.assertEqual(agent['pid'], os.getpid())

        component = payload['components'][0]

        self.assertEqual(component['name'], 'NAME')
        self.assertEqual(component['guid'], 'GUID')
        self.assertEqual(component['duration'], 123)
        self.assertEqual(component['metrics'], [])

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_payload_not_jsonable_request(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=200, content='{"status":"RESULT"}')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(DiscardDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, (object,))

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_compressed_data_small(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=200, content='{"status":"RESULT"}')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        guid = 64*1024*'X'

        result = session_instance.send_metric_data(
                'NAME', guid, 'VERSION', 123, ())

        self.assertEqual(result, 'RESULT')

        self.assertTrue(requests_session_object.post.called)

        (url,), kwargs = requests_session_object.post.call_args

        data = zlib.decompress(kwargs['data']).decode('Latin-1')
        payload = json.loads(data)

        agent = payload['agent']

        self.assertEqual(agent['version'], 'VERSION')
        self.assertEqual(agent['host'], socket.gethostname())
        self.assertEqual(agent['pid'], os.getpid())

        component = payload['components'][0]

        self.assertEqual(component['name'], 'NAME')
        self.assertEqual(component['guid'], guid)
        self.assertEqual(component['duration'], 123)
        self.assertEqual(component['metrics'], [])

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_compressed_data_large(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=200, content='{"status":"RESULT"}')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        guid = 2000000*'X'

        result = session_instance.send_metric_data(
                'NAME', guid, 'VERSION', 123, ())

        self.assertEqual(result, 'RESULT')

        self.assertTrue(requests_session_object.post.called)

        (url,), kwargs = requests_session_object.post.call_args

        data = zlib.decompress(kwargs['data']).decode('Latin-1')
        payload = json.loads(data)

        agent = payload['agent']

        self.assertEqual(agent['version'], 'VERSION')
        self.assertEqual(agent['host'], socket.gethostname())
        self.assertEqual(agent['pid'], os.getpid())

        component = payload['components'][0]

        self.assertEqual(component['name'], 'NAME')
        self.assertEqual(component['guid'], guid)
        self.assertEqual(component['duration'], 123)
        self.assertEqual(component['metrics'], [])

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_requests_exception(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post = mock.Mock(
                side_effect=requests.RequestException)

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(RetryDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False,
                proxy_host='PROXY', proxy_port=1234)
        session_instance = interface.create_session()

        self.assertRaises(RetryDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_http_400_error(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=400, content='CONTENT')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(DiscardDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_http_400_error_deflate(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=400, content='CONTENT')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        guid = 64*1024*'X'

        self.assertRaises(DiscardDataForRequest,
                session_instance.send_metric_data, 'NAME', guid,
                'VERSION', 123, ())

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_http_403_error(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=403, content='CONTENT')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(DiscardDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_http_413_error(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=413, content='CONTENT')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(DiscardDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_http_503_error(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=503, content='CONTENT')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(ServerIsUnavailable,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_http_504_error(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=504, content='CONTENT')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(ServerIsUnavailable,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_http_500_error(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=500, content='CONTENT')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(DiscardDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False,
                proxy_host='PROXY', proxy_port=1234)
        session_instance = interface.create_session()

        self.assertRaises(DiscardDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_not_json_response(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=200, content='NOT-JSON')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(DiscardDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

    @mock.patch('newrelic.packages.requests.session')
    def test_remote_service_error(self, requests_session_mock):

        requests_session_object = mock.MagicMock()
        requests_session_object.post.return_value = mock.MagicMock(
                status_code=200, content='{"error":"ERROR"}')

        requests_session_mock.return_value = requests_session_object

        interface = PlatformInterface('LICENSE-KEY', host='HOST', ssl=False)
        session_instance = interface.create_session()

        self.assertRaises(DiscardDataForRequest,
                session_instance.send_metric_data, 'NAME', 'GUID',
                'VERSION', 123, ())

        session_instance.close_connection()

if __name__ == '__main__':
    unittest.main()
