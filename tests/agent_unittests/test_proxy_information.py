from newrelic.core.config import global_settings
from newrelic.core.data_collector import proxy_server, connection_type

import pytest

_connection_combinations = (
    (None, None, None, 'direct/https'),
    (None, 'http://localhost:8888', None, 'http-proxy/https'),
    (None, 'https://localhost:8888', None, 'https-proxy/https'),
    (None, 'localhost', 8888, 'https-proxy/https'),
    ('http', 'localhost', 8888, 'http-proxy/https'),
    ('https', 'localhost', 8888, 'https-proxy/https'),
)

@pytest.mark.parametrize(('proxy_scheme', 'proxy_host', 'proxy_port',
        'expected'), _connection_combinations)
def test_connection_type(proxy_scheme, proxy_host, proxy_port, expected):
    settings = global_settings()

    original_proxy_scheme = settings.proxy_scheme
    original_proxy_host = settings.proxy_host
    original_proxy_port = settings.proxy_port

    settings.proxy_scheme = proxy_scheme
    settings.proxy_host = proxy_host
    settings.proxy_port = proxy_port

    try:
        proxies = proxy_server()
        type = connection_type(proxies)
        assert type == expected

    finally:
        settings.proxy_scheme = original_proxy_scheme
        settings.proxy_host = original_proxy_host
        settings.proxy_port = original_proxy_port
