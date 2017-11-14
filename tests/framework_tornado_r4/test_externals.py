import pytest
from testing_support.fixtures import (validate_transaction_metrics,
        override_application_settings)

from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)


@pytest.mark.parametrize('client_class',
        ['AsyncHTTPClient', 'CurlAsyncHTTPClient'])
@pytest.mark.parametrize('cat_enabled', [True, False])
@pytest.mark.parametrize('request_type', ['uri', 'class'])
def test_async_httpclient(app, cat_enabled, request_type, client_class):

    if cat_enabled:
        external = MockExternalHTTPHResponseHeadersServer()
        port = external.port
        uri = '/async-client/%s/%s/%s' % (port, request_type, client_class)
    else:
        port = app.get_http_port()
        uri = '/async-client/%s/%s/%s' % (port, request_type, client_class)

    expected_metrics = [
        ('External/localhost:%s/tornado.httpclient/GET' % port, 1)
    ]

    @override_application_settings(
            {'cross_application_tracer.enabled': cat_enabled})
    @validate_transaction_metrics(
        '_target_application:AsyncExternalHandler.get',
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics
    )
    def _test():
        if cat_enabled:
            with external:
                response = app.fetch(uri)
        else:
            response = app.fetch(uri)

        assert response.code == 200

        if cat_enabled:
            # Check that we sent CAT headers
            required_headers = (b'X-NewRelic-ID', b'X-NewRelic-Transaction')
            forgone_headers = (b'X-NewRelic-App-Data',)

            sent_headers = response.body

            for header in required_headers:
                assert header in sent_headers, (header, sent_headers)

            for header in forgone_headers:
                assert header not in sent_headers, (header, sent_headers)
        else:
            sent_headers = response.body
            if hasattr(sent_headers, 'decode'):
                sent_headers = sent_headers.decode('utf-8')

            # new relic shouldn't add anything to the outgoing
            assert 'x-newrelic' not in sent_headers, sent_headers

    _test()


@pytest.mark.parametrize('client_class',
        ['AsyncHTTPClient', 'CurlAsyncHTTPClient'])
@validate_transaction_metrics('_target_application:InvalidExternalMethod.get')
def test_httpclient_invalid_method(app, client_class):
    uri = '/client-invalid-method/%s' % client_class
    response = app.fetch(uri)
    assert response.code == 503


@pytest.mark.parametrize('client_class',
        ['AsyncHTTPClient', 'CurlAsyncHTTPClient'])
@validate_transaction_metrics('_target_application:InvalidExternalKwarg.get')
def test_httpclient_invalid_kwarg(app, client_class):
    uri = '/client-invalid-kwarg/%s' % client_class
    response = app.fetch(uri)
    assert response.code == 503
