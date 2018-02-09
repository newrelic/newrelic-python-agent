import pytest
import tempfile

INI_FILE_WITHOUT_LICENSE_KEY = b"""
[newrelic]
"""

NO_REGION_KEY = '66c637a29c3982469a3fe8d1982d002c4a'
INI_FILE_NON_REGION_AWARE_LICENSE_KEY = b"""
[newrelic]
license_key = %s
""" % NO_REGION_KEY.encode('utf-8')

EU01_KEY = 'eu01xx66c637a29c3982469a3fe8d1982d002c4a'
INI_FILE_EU01_LICENSE_KEY = b"""
[newrelic]
license_key = %s
""" % EU01_KEY.encode('utf-8')

INI_FILE_HOST_OVERRIDE = b"""
[newrelic]
host = staging-collector.newrelic.com
license_key = %s
""" % EU01_KEY.encode('utf-8')

try:
    # python 2.x
    reload
except NameError:
    # python 3.x
    from imp import reload


@pytest.fixture(scope='function')
def global_settings(request, monkeypatch):
    ini_contents = request.getfixturevalue('ini')

    monkeypatch.delenv('NEW_RELIC_HOST', raising=False)
    monkeypatch.delenv('NEW_RELIC_LICENSE_KEY', raising=False)

    if 'env' in request.funcargnames:
        env = request.getfixturevalue('env')
        for k, v in env.items():
            monkeypatch.setenv(k, v)

    import newrelic.config as config
    import newrelic.core.config as core_config
    reload(core_config)
    reload(config)

    ini_file = tempfile.NamedTemporaryFile()
    ini_file.write(ini_contents)
    ini_file.seek(0)

    config.initialize(ini_file.name)

    yield core_config.global_settings


# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize('ini,env,expected_host,expected_license_key', [
    (INI_FILE_WITHOUT_LICENSE_KEY, {}, 'collector.newrelic.com', None),
    (INI_FILE_WITHOUT_LICENSE_KEY,
            {'NEW_RELIC_LICENSE_KEY': EU01_KEY},
            'collector.eu01.nr-data.net', EU01_KEY),
    (INI_FILE_NON_REGION_AWARE_LICENSE_KEY, {}, 'collector.newrelic.com',
            NO_REGION_KEY),
    (INI_FILE_EU01_LICENSE_KEY, {}, 'collector.eu01.nr-data.net', EU01_KEY),
])
def test_region_aware_license_keys(ini, env, expected_host,
        expected_license_key, global_settings):

    settings = global_settings()
    assert settings.host == expected_host
    assert settings.license_key == expected_license_key


@pytest.mark.parametrize('ini,env,expected_host,expected_license_key', [
    (INI_FILE_WITHOUT_LICENSE_KEY,
            {'NEW_RELIC_HOST': 'staging-collector.newrelic.com',
                'NEW_RELIC_LICENSE_KEY': EU01_KEY},
            'staging-collector.newrelic.com',
            EU01_KEY),
    (INI_FILE_EU01_LICENSE_KEY,
            {'NEW_RELIC_HOST': 'staging-collector.newrelic.com'},
            'staging-collector.newrelic.com',
            EU01_KEY),
    (INI_FILE_HOST_OVERRIDE, {}, 'staging-collector.newrelic.com', EU01_KEY),
    (INI_FILE_HOST_OVERRIDE,
            {'NEW_RELIC_HOST': 'evil-collector.newrelic.com',
                'NEW_RELIC_LICENSE_KEY': EU01_KEY},
            'staging-collector.newrelic.com', EU01_KEY),
])
def test_host_overrides(ini, env, expected_host, expected_license_key,
        global_settings):

    settings = global_settings()
    assert settings.host == expected_host
    assert settings.license_key == expected_license_key
