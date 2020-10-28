# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

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


@pytest.mark.parametrize("ini,license_key,host_override,expected_host", (
    (INI_FILE_WITHOUT_LICENSE_KEY, NO_REGION_KEY, None, "collector.newrelic.com"),
    (INI_FILE_WITHOUT_LICENSE_KEY, EU01_KEY, None, "collector.eu01.nr-data.net"),
    (INI_FILE_WITHOUT_LICENSE_KEY, NO_REGION_KEY, "foo.newrelic.com", "foo.newrelic.com"),
))
def test_region_aware_global_settings(ini, license_key, host_override,
        expected_host, global_settings):
    settings = global_settings()

    if host_override:
        settings.host = host_override

    settings.license_key = license_key
    assert settings.host == expected_host
