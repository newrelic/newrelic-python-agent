import pytest
from newrelic.core.stats_engine import CustomMetrics
from newrelic.core.internal_metrics import InternalTraceContext

INI_FILE_EMPTY = b"""
[newrelic]
"""


INI_FILE_INFINITE_TRACING = b"""
[newrelic]
infinite_tracing.trace_observer_url = http://y
infinite_tracing.span_queue_size = 2000
"""


# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize('ini,env,expected_scheme,expected_netloc', (
    (INI_FILE_EMPTY, {}, None, None),
    (INI_FILE_EMPTY,
     {'NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_URL': 'https://x'},
     'https', 'x'),
    (INI_FILE_INFINITE_TRACING,
     {'NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_URL': 'https://x'},
     'http', 'y'),
))
def test_infinite_tracing_settings(ini, env,
        expected_scheme, expected_netloc, global_settings):

    settings = global_settings()
    if expected_scheme is None:
        assert settings.infinite_tracing.trace_observer_url is None
    else:
        assert settings.infinite_tracing.trace_observer_url.scheme == expected_scheme
        assert settings.infinite_tracing.trace_observer_url.netloc == expected_netloc


# Tests for loading Infinite Tracing span queue size setting
# and testing values precedence
@pytest.mark.parametrize('ini,env,expected_size', (
    (INI_FILE_EMPTY, {}, 10000),
    (INI_FILE_EMPTY,
     {'NEW_RELIC_INFINITE_TRACING_SPAN_QUEUE_SIZE': 'invalid'},
     10000),
    (INI_FILE_EMPTY,
     {'NEW_RELIC_INFINITE_TRACING_SPAN_QUEUE_SIZE': 5000},
     5000),
    (INI_FILE_INFINITE_TRACING,
     {'NEW_RELIC_INFINITE_TRACING_SPAN_QUEUE_SIZE': 3000},
     2000),
))
def test_infinite_tracing_span_queue_size(ini, env,
        expected_size, global_settings):

    settings = global_settings()
    assert settings.infinite_tracing.span_queue_size == expected_size
