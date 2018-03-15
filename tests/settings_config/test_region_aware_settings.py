import pytest
import tempfile

INI_FILE_WITHOUT_LICENSE_KEY = b"""
[newrelic]
"""

NO_REGION_KEY = '66c637a29c3982469a3fe8d1982d002c4a'
INI_FILE_NO_REGION_KEY = """
[newrelic]
license_key = %s
""" % NO_REGION_KEY
INI_FILE_NO_REGION_KEY = INI_FILE_NO_REGION_KEY.encode('utf-8')

EU01_KEY = 'eu01xx66c637a29c3982469a3fe8d1982d002c4a'
INI_FILE_EU01_KEY = """
[newrelic]
license_key = %s
""" % EU01_KEY
INI_FILE_EU01_KEY = INI_FILE_EU01_KEY.encode('utf-8')

INI_FILE_HOST_OVERRIDE = """
[newrelic]
host = staging-collector.newrelic.com
license_key = %s
""" % EU01_KEY
INI_FILE_HOST_OVERRIDE = INI_FILE_HOST_OVERRIDE.encode('utf-8')

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


STAGING_HOST = 'staging-collector.newrelic.com'
STAGING_HOST_ENV = {'NEW_RELIC_HOST': STAGING_HOST}
EVIL_COLLECTOR_HOST_ENV = {'NEW_RELIC_HOST': 'evil-collector.newrelic.com'}

NO_REGION_ENV = {'NEW_RELIC_LICENSE_KEY': NO_REGION_KEY}
EU_REGION_ENV = {'NEW_RELIC_LICENSE_KEY': EU01_KEY}
EU01_HOST = 'collector.eu01.nr-data.net'

DEFAULT_HOST = 'collector.newrelic.com'


# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize('ini,env,expected_host,expected_license_key', [
    # Test license key parsing (no env vars needed since we're not testing
    # precedence)
    (INI_FILE_NO_REGION_KEY, {}, 'collector.newrelic.com', NO_REGION_KEY),
    (INI_FILE_EU01_KEY, {}, 'collector.eu01.nr-data.net', EU01_KEY),

    # Test precedence
    # 1. host in config file (this trumps all)
    (INI_FILE_HOST_OVERRIDE, EVIL_COLLECTOR_HOST_ENV, STAGING_HOST, EU01_KEY),

    # 2. host in environment variable (overrides parsed host)
    (INI_FILE_EU01_KEY, STAGING_HOST_ENV, STAGING_HOST, EU01_KEY),

    # 3. host parsed by license key in config file
    (INI_FILE_EU01_KEY, NO_REGION_ENV, EU01_HOST, EU01_KEY),
    (INI_FILE_NO_REGION_KEY, EU_REGION_ENV, DEFAULT_HOST, NO_REGION_KEY),

    # 4. host parsed by license key in env variable
    (INI_FILE_WITHOUT_LICENSE_KEY, EU_REGION_ENV, EU01_HOST, EU01_KEY),
    (INI_FILE_WITHOUT_LICENSE_KEY, NO_REGION_ENV, DEFAULT_HOST, NO_REGION_KEY),

    # 5. defaults to collector.newrelic.com (no license key specified)
    (INI_FILE_WITHOUT_LICENSE_KEY, {}, DEFAULT_HOST, None),
])
def test_region_aware_license_keys(ini, env, expected_host,
        expected_license_key, global_settings):

    settings = global_settings()
    assert settings.host == expected_host
    assert settings.license_key == expected_license_key
