from newrelic.agent import global_settings
from newrelic.core.data_collector import proxy_server, connection_type

import pytest

_connection_combinations = (
    (False, None, None, None, 'direct/http'),
    (True, None, None, None, 'direct/https'),
    (False, None, 'http://localhost:8888', None, 'http-proxy/http'),
    (True, None, 'http://localhost:8888', None, 'http-proxy/https'),
    (False, None, 'https://localhost:8888', None, 'https-proxy/http'),
    (True, None, 'https://localhost:8888', None, 'https-proxy/https'),
    (False, None, 'localhost', 8888, 'http-proxy/http'),
    (True, None, 'localhost', 8888, 'https-proxy/https'),
    (False, 'http', 'localhost', 8888, 'http-proxy/http'),
    (True, 'http', 'localhost', 8888, 'http-proxy/https'),
    (False, 'https', 'localhost', 8888, 'https-proxy/http'),
    (True, 'https', 'localhost', 8888, 'https-proxy/https'),
)

@pytest.mark.parametrize(('ssl', 'proxy_scheme', 'proxy_host', 'proxy_port',
        'expected'), _connection_combinations)
def test_connection_type(ssl, proxy_scheme, proxy_host, proxy_port, expected):
    settings = global_settings()

    original_ssl = settings.ssl
    original_proxy_scheme = settings.proxy_scheme
    original_proxy_host = settings.proxy_host
    original_proxy_port = settings.proxy_port

    settings.ssl = ssl
    settings.proxy_scheme = proxy_scheme
    settings.proxy_host = proxy_host
    settings.proxy_port = proxy_port

    try:
        proxies = proxy_server()
        type = connection_type(proxies)
        assert type == expected

    finally:
        settings.ssl = original_ssl
        settings.proxy_scheme = original_proxy_scheme
        settings.proxy_host = original_proxy_host
        settings.proxy_port = original_proxy_port
