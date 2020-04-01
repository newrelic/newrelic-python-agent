import pytest
from newrelic.core.data_collector import parse_infinite_tracing_endpoint
from newrelic.core.stats_engine import CustomMetrics
from newrelic.core.internal_metrics import InternalTraceContext

INI_FILE_EMPTY = b"""
[newrelic]
"""


INI_FILE_INFINITE_TRACING = b"""
[newrelic]
infinite_tracing.trace_observer_url = bar
"""


INI_FILE_SPAN_QUEUE = b"""
[newrelic]
infinite_tracing.trace_observer_uri = bar
infinite_tracing.span_queue_size = 2000
"""


# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize('ini,env,expected_endpoint', (
    (INI_FILE_EMPTY, {}, None),
    (INI_FILE_EMPTY,
     {'NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_URL': 'foo'},
     'foo'),
    (INI_FILE_INFINITE_TRACING,
     {'NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_URL': 'foo'},
     'bar'),
))
def test_infinite_tracing_settings(ini, env,
        expected_endpoint, global_settings):

    settings = global_settings()
    assert settings.infinite_tracing.trace_observer_url == expected_endpoint


# Tests for loading Infinite Tracing span queue size setting
# and testing values precedence
@pytest.mark.parametrize('ini,env,expected_size', (
    (INI_FILE_EMPTY, {}, 10000),
    (INI_FILE_INFINITE_TRACING,
     {'NEW_RELIC_INFINITE_TRACING_SPAN_QUEUE_SIZE': 'invalid'},
     10000),
    (INI_FILE_INFINITE_TRACING,
     {'NEW_RELIC_INFINITE_TRACING_SPAN_QUEUE_SIZE': 5000},
     5000),
    (INI_FILE_SPAN_QUEUE,
     {'NEW_RELIC_INFINITE_TRACING_SPAN_QUEUE_SIZE': 3000},
     2000),
))
def test_infinite_tracing_span_queue_size(ini, env,
        expected_size, global_settings):

    settings = global_settings()
    assert settings.infinite_tracing.span_queue_size == expected_size


# Testing valid and invalid endpoints, including leading
# slashes, endpoints without both scheme and authority, etc
@pytest.mark.parametrize('endpoint, expected_components', (
    ('https://test.tracing.edge.nr-data.net/',
     ('https', 'test.tracing.edge.nr-data.net')),
    ('https://test.tracing.edge.nr-data.net:8080/',
     ('https', 'test.tracing.edge.nr-data.net:8080')),
    ('http://test.tracing.edge.nr-data.net',
     ('http', 'test.tracing.edge.nr-data.net')),
    ('http://test.tracing.edge.nr-data.net/v1/',
     ('http', 'test.tracing.edge.nr-data.net')),
    (None, None),
    ('', None),
    ('https:///', None),
    ('//test.tracing.edge.nr-data.net:8080/', None),
    (123, None)
))
def test_infinite_tracing_endpoint(endpoint, expected_components):
    internal_metrics = CustomMetrics()
    with InternalTraceContext(internal_metrics):
        parsed_endpoint = parse_infinite_tracing_endpoint(endpoint)
        metrics = list(internal_metrics.metrics())

        if expected_components:
            assert parsed_endpoint.scheme == expected_components[0]
            assert parsed_endpoint.netloc == expected_components[1]
            assert not metrics
        else:
            assert parsed_endpoint is None
            if endpoint is None:
                assert not metrics
            else:
                assert metrics[0] == (
                    'Supportability/InfiniteTracing/MalformedTraceObserver',
                    [1, 0.0, 0.0, 0.0, 0.0, 0.0])
