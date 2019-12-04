import pytest

INI_FILE_EMPTY = b"""
[newrelic]
"""


INI_FILE_W3C = b"""
[newrelic]
distributed_tracing.format = w3c
"""

# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize('ini,env,expected_format', (
    (INI_FILE_EMPTY, {}, 'newrelic',),
    (INI_FILE_W3C, {}, 'w3c'),
))
def test_region_aware_license_keys(ini, env, expected_format, global_settings):

    settings = global_settings()
    assert settings.distributed_tracing.format == expected_format
