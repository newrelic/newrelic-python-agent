import pytest

from newrelic.core.data_collector import (collector_url, proxy_server,
        connection_type)
from newrelic.core.config import global_settings
from testing_support.fixtures import override_generic_settings


@pytest.mark.parametrize('server', [None, 'http://fake'])
@pytest.mark.parametrize('ssl_setting', [True, False])
def test_collector_url_independent_of_ssl_setting(server, ssl_setting):

    settings = global_settings()

    @override_generic_settings(settings, {'ssl': ssl_setting})
    def _test():
        url = collector_url(server)
        assert url.startswith('https://')

    _test()


@pytest.mark.parametrize('ssl_setting', [True, False])
def test_proxy_scheme_assumes_ssl(ssl_setting):
    settings = global_settings()

    @override_generic_settings(settings,
            {'ssl': ssl_setting,
            'proxy_scheme': None,
            'proxy_host': 'kittens',
            'proxy_port': 8080})
    def _test():
        proxy_details = proxy_server()
        for url in proxy_details.values():
            assert url.startswith('https://')

    _test()


@pytest.mark.parametrize('ssl_setting', [True, False])
def test_connection_type_metric_assumes_ssl(ssl_setting):
    settings = global_settings()

    @override_generic_settings(settings, {'ssl': ssl_setting})
    def _test():
        metric = connection_type(None)
        assert metric.endswith('/https')

    _test()
