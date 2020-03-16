import pytest

INI_FILE_EMPTY = b"""
[newrelic]
"""


INI_FILE_MTB = b"""
[newrelic]
mtb.endpoint = bar
"""

# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize('ini,env,expected_endpoint', (
    (INI_FILE_EMPTY, {}, None),
    (INI_FILE_EMPTY, {'NEW_RELIC_MTB_ENDPOINT': 'foo'}, 'foo'),
    (INI_FILE_MTB, {'NEW_RELIC_MTB_ENDPOINT': 'foo'}, 'bar'),
))
def test_mtb_settings(ini, env, expected_endpoint, global_settings):

    settings = global_settings()
    assert settings.mtb.endpoint == expected_endpoint
