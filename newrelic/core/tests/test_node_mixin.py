from newrelic.core.node_mixin import GenericNodeMixin
from newrelic.core.attribute import DST_ALL
from newrelic.core.attribute_filter import AttributeFilter
from newrelic.core.config import global_settings_dump

ATTRIBUTE_FILTER = AttributeFilter(global_settings_dump())


class Node(GenericNodeMixin):
    agent_attributes = {'foo': 'bar'}


def test_resolve_agent_attributes_uncached():
    node = Node()
    params = node.resolve_agent_attributes(ATTRIBUTE_FILTER, DST_ALL)
    assert len(params) == 1
    assert params['foo'] == 'bar'
    assert node._agent_attributes_destinations.get('foo') is not None


def test_resolve_agent_attributes_cached():
    node = Node()
    destinations_cached = {'foo': DST_ALL}
    node._agent_attributes_destinations = destinations_cached

    params = node.resolve_agent_attributes(ATTRIBUTE_FILTER, DST_ALL)
    assert len(params) == 1
    assert params['foo'] == 'bar'
    assert node._agent_attributes_destinations is destinations_cached
