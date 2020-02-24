import pytest
import newrelic.core.external_node

_external_node = newrelic.core.external_node.ExternalNode(
    library='lib',
    url='http://example.com/foo?bar=1',
    method='GET',
    children=(),
    start_time=0.0,
    end_time=0.0,
    duration=0.0,
    exclusive=0.0,
    params={},
    is_async=False,
    guid=None,
    agent_attributes={},
    user_attributes={},
)


@pytest.fixture(autouse=True)
def cleanup_caches():
    for attr in ('_details', '_http_url'):
        if hasattr(_external_node, attr):
            delattr(_external_node, attr)


def test_url_details_cache():
    _external_node._details = 'FOO'
    assert _external_node.details == 'FOO'


def test_http_url_cache():
    _external_node._http_url = 'BAR'
    assert _external_node.http_url == 'BAR'


def test_http_url_value():
    assert _external_node.http_url == 'http://example.com/foo'
