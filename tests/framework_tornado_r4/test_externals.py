import io
import pytest
import socket
import threading
import tornado

from wsgiref.simple_server import make_server

from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
        override_application_settings)
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)


ENCODING_KEY = '1234567890123456789012345678901234567890'


@pytest.fixture(scope='module')
def external():
    external = MockExternalHTTPHResponseHeadersServer()
    with external:
        yield external


def _get_open_port():
    # https://stackoverflow.com/questions/2838244/get-open-tcp-port-in-python/2838309#2838309
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


@background_task(name='make_request')
def make_request(port, req_type, client_cls, count=1, raise_error=True,
        **kwargs):
    import tornado.gen
    import tornado.httpclient
    import tornado.curl_httpclient
    import tornado.ioloop

    class CustomAsyncHTTPClient(tornado.httpclient.AsyncHTTPClient):
        def fetch_impl(self, request, callback):
            body = str(request.headers).encode('utf-8')
            response = tornado.httpclient.HTTPResponse(request=request,
                    code=200, buffer=io.BytesIO(body))
            callback(response)

    if client_cls == 'AsyncHTTPClient':
        client = tornado.httpclient.AsyncHTTPClient()
    elif client_cls == 'CurlAsyncHTTPClient':
        client = tornado.curl_httpclient.CurlAsyncHTTPClient()
    elif client_cls == 'HTTPClient':
        client = tornado.httpclient.HTTPClient()
    elif client_cls == 'CustomAsyncHTTPClient':
        client = CustomAsyncHTTPClient()
    else:
        raise ValueError("Received unknown client type: %s" % client_cls)

    uri = 'http://localhost:%s/echo-headers' % port
    if req_type == 'class':
        req = tornado.httpclient.HTTPRequest(uri, **kwargs)
        kwargs = {}
    elif req_type == 'uri':
        req = uri
    else:
        raise ValueError("Received unknown request type: %s" % req_type)

    @tornado.gen.coroutine
    def _make_request():

        futures = [client.fetch(req, raise_error=raise_error, **kwargs)
                for _ in range(count)]
        responses = yield tornado.gen.multi(futures)
        response = responses[0]

        raise tornado.gen.Return(response)

    if client_cls == 'HTTPClient':
        for _ in range(count):
            response = client.fetch(req, raise_error=raise_error, **kwargs)
        return response
    else:
        response = tornado.ioloop.IOLoop.current().run_sync(_make_request)
        return response


@pytest.mark.skipif(tornado.version_info < (4, 5), strict=True,
        reason='PYTHON-2641')
@pytest.mark.parametrize('client_class',
        ['AsyncHTTPClient', 'CurlAsyncHTTPClient', 'HTTPClient',
            'CustomAsyncHTTPClient'])
@pytest.mark.parametrize('cat_enabled,user_header', [
    (True, None),
    (True, 'X-NewRelic-ID'),
    (True, 'X-NewRelic-Transaction'),
    (False, None),
])
@pytest.mark.parametrize('request_type', ['uri', 'class'])
@pytest.mark.parametrize('num_requests', [1, 2])
def test_httpclient(cat_enabled, request_type, client_class,
        user_header, num_requests, external):

    port = external.port

    expected_metrics = [
        ('External/localhost:%s/tornado.httpclient/GET' % port, num_requests)
    ]

    @override_application_settings(
            {'cross_application_tracer.enabled': cat_enabled})
    @validate_transaction_metrics(
        'make_request',
        background_task=True,
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics
    )
    def _test():
        headers = {}
        if user_header:
            headers = {user_header: 'USER'}

        response = make_request(port, request_type, client_class,
                headers=headers, count=num_requests)
        assert response.code == 200

        sent_headers = response.body

        # User headers override all inserted NR headers
        if user_header:
            header_str = '%s: USER' % user_header
            header_str = header_str.encode('utf-8')
            assert header_str in sent_headers, (header_str, sent_headers)

        if cat_enabled:
            # Check that we sent CAT headers
            assert b'X-NewRelic-ID' in sent_headers
            assert b'X-NewRelic-Transaction' in sent_headers

            assert b'X-NewRelic-App-Data' not in sent_headers
        else:
            if hasattr(sent_headers, 'decode'):
                sent_headers = sent_headers.decode('utf-8')

            # new relic shouldn't add anything to the outgoing
            sent_headers = sent_headers.lower()
            assert 'x-newrelic' not in sent_headers, sent_headers

    _test()


@pytest.mark.skipif(tornado.version_info < (4, 5), reason='PYTHON-2641')
@pytest.mark.parametrize('client_class',
        ['AsyncHTTPClient', 'CurlAsyncHTTPClient', 'HTTPClient'])
@pytest.mark.parametrize('cat_enabled', [True, False])
@pytest.mark.parametrize('request_type', ['uri', 'class'])
@pytest.mark.parametrize('response_code,raise_error', [
    (500, True),
    (500, False),
    (200, False),
])
def test_client_cat_response_processing(cat_enabled, request_type,
        client_class, raise_error, response_code):
    _custom_settings = {
        'cross_process_id': '1#1',
        'encoding_key': ENCODING_KEY,
        'trusted_account_ids': [1],
        'cross_application_tracer.enabled': cat_enabled,
        'transaction_tracer.transaction_threshold': 0.0,
    }

    def _response_app(environ, start_response):
        # payload
        # (
        #     u'1#1', u'WebTransaction/Function/app:beep',
        #     0, 1.23, -1,
        #     'dd4a810b7cb7f937',
        #     False,
        # )
        response_headers = [('X-NewRelic-App-Data',
                'ahACFwQUGxpuVVNmQVVbRVZbTVleXBxyQFhUTFBfXx1SREUMV'
                'V1cQBMeAxgEGAULFR0AHhFQUQJWAAgAUwVQVgJQDgsOEh1UUlhGU2o='), ]
        start_response('%d kittens' % response_code, response_headers)
        return [b'BEEEEEP']

    wsgi_port = _get_open_port()
    server = make_server('127.0.0.1', wsgi_port, _response_app)

    expected_metrics = [
        ('ExternalTransaction/localhost:%s/1#1/WebTransaction/'
                'Function/app:beep' % wsgi_port, 1 if cat_enabled else None),
    ]

    @validate_transaction_metrics(
        'make_request',
        background_task=True,
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics
    )
    @override_application_settings(_custom_settings)
    def _test():
        import tornado.httpclient
        try:
            response = make_request(wsgi_port, request_type, client_class,
                    raise_error=raise_error)
        except tornado.httpclient.HTTPError as e:
            assert raise_error
            response = e.response
        else:
            assert not raise_error

        assert response.code == response_code

    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()
    _test()
    server_thread.join(0.1)


@pytest.mark.skipif(tornado.version_info < (4, 5), strict=True,
    reason='PYTHON-2629')
@pytest.mark.parametrize('client_class', ['AsyncHTTPClient',
    'CurlAsyncHTTPClient', 'HTTPClient'])
@validate_transaction_metrics('make_request',
        background_task=True)
def test_httpclient_invalid_method(client_class, external):
    with pytest.raises(KeyError):
        make_request(external.port, 'uri', client_class,
                method='COOKIES')


@pytest.mark.parametrize('client_class',
        ['AsyncHTTPClient', 'CurlAsyncHTTPClient', 'HTTPClient'])
@validate_transaction_metrics('make_request',
        background_task=True)
def test_httpclient_invalid_kwarg(client_class, external):
    with pytest.raises(TypeError):
        make_request(external.port, 'uri', client_class, boop='1234')


@validate_transaction_metrics('_target_application:CrashClientHandler.get',
    rollup_metrics=[('External/example.com/tornado.httpclient/GET', 1)],
    scoped_metrics=[('External/example.com/tornado.httpclient/GET', 1)]
)
def test_httpclient_fetch_crashes(app):
    response = app.fetch('/crash-client')
    assert response.code == 200


@validate_transaction_metrics('_target_application:CrashClientHandler.get',
    rollup_metrics=[('External/example.com/tornado.httpclient/GET', None)],
    scoped_metrics=[('External/example.com/tornado.httpclient/GET', None)]
)
def test_httpclient_fetch_inside_terminal_node(app):
    # Test that our instrumentation correctly handles the case when the parent
    # is a terminal node

    # This is protecting against a "pop_current" when the external trace never
    # actually gets pushed
    response = app.fetch('/client-terminal-trace')
    assert response.code == 200
