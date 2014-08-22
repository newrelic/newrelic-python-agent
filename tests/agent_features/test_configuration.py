import pytest

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from newrelic.core.config import (global_settings_dump,
    apply_config_setting, Settings)

def parameterize_local_config(settings_list):
    settings_object_list = []

    for settings in settings_list:
        settings_object = Settings()
        for name, value in settings.items():
            apply_config_setting(settings_object, name, value)
        settings_object_list.append(settings_object)

    return pytest.mark.parametrize('settings', settings_object_list)

_test_strip_proxy_details_local_configs = [
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': None,
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': None,
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'hostname',
        'proxy_port': 8888,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'hostname',
        'proxy_port': 8888,
        'proxy_user': 'username',
        'proxy_pass': 'password',

        'expected_proxy_host': 'hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'http://hostname',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'http://hostname:8888',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://hostname:8888',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'http://hostname',
        'proxy_port': None,
        'proxy_user': 'username',
        'proxy_pass': 'password',

        'expected_proxy_host': 'http://hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'http://hostname:8888',
        'proxy_port': None,
        'proxy_user': 'username',
        'proxy_pass': 'password',

        'expected_proxy_host': 'http://hostname:8888',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'http://username@hostname',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'http://username@hostname:8888',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://hostname:8888',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'http://username:password@hostname',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'http://username:password@hostname:8888',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'http://hostname:8888',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'https://username:password@hostname',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'https://hostname',
    },
    {
        'license_key': 'LICENSE-KEY',
        'api_key': 'API-KEY',

        'proxy_scheme': None,
        'proxy_host': 'https://username:password@hostname:8888',
        'proxy_port': None,
        'proxy_user': None,
        'proxy_pass': None,

        'expected_proxy_host': 'https://hostname:8888',
    },
]

@parameterize_local_config(_test_strip_proxy_details_local_configs)
def test_strip_proxy_details(settings):
    assert 'license_key' in settings
    assert 'api_key' in settings

    assert 'proxy_scheme' in settings
    assert 'proxy_host' in settings
    assert 'proxy_port' in settings
    assert 'proxy_user' in settings
    assert 'proxy_port' in settings

    stripped = global_settings_dump(settings)

    # These should always be deleted.

    assert 'license_key' not in stripped
    assert 'api_key' not in stripped

    assert 'proxy_user' not in stripped
    assert 'proxy_pass' not in stripped

    # The proxy_host and proxy_port will be preserved but proxy_host
    # needs to be checked to make sure it doesn't contain a username and
    # password. Do this through parsing to make sure not breaking the
    # structure in some way and also direct comparison of what is
    # expected as backup.

    assert 'proxy_scheme' in settings
    assert 'proxy_host' in stripped
    assert 'proxy_port' in stripped

    proxy_host = stripped['proxy_host']
    expected_proxy_host = stripped['expected_proxy_host']

    if proxy_host is not None:
        components = urlparse.urlparse(proxy_host)

        assert not components.username
        assert not components.password

    assert proxy_host == expected_proxy_host
