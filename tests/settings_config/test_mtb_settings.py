import pytest
from newrelic.core.data_collector import parse_infinite_tracing_endpoint
from newrelic.core.stats_engine import CustomMetrics
from newrelic.core.internal_metrics import InternalTraceContext

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
