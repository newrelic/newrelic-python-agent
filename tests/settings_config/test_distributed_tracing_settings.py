import pytest

INI_FILE_EMPTY = b"""
[newrelic]
"""


INI_FILE_W3C = b"""
[newrelic]
distributed_tracing.exclude_newrelic_header = true
"""

# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize('ini,env,expected_format', (
    (INI_FILE_EMPTY, {}, False),
    (INI_FILE_W3C, {}, True),
))
def test_distributed_trace_setings(ini, env, expected_format, global_settings):

    settings = global_settings()
    assert settings.distributed_tracing.exclude_newrelic_header == expected_format
