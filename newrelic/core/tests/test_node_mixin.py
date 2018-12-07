from newrelic.core.node_mixin import GenericNodeMixin
from newrelic.core.attribute import DST_ALL, Attribute
from newrelic.core.attribute_filter import AttributeFilter
from newrelic.core.config import global_settings_dump

ATTRIBUTE_FILTER = AttributeFilter(global_settings_dump())


class Node(GenericNodeMixin):
    agent_attributes = {'foo': 'bar'}


def test_resolve_agent_attributes_uncached():
    node = Node()
    attrs = node.resolve_agent_attributes(ATTRIBUTE_FILTER)
    assert len(attrs) == 1
    assert attrs[0].name == 'foo'
    assert node._agent_attributes_resolved is attrs


def test_resolve_agent_attributes_cached():
    node = Node()
    attr = Attribute('k', 'v', DST_ALL)
    attrs_cached = [attr]
    node._agent_attributes_resolved = attrs_cached
    attrs = node.resolve_agent_attributes(ATTRIBUTE_FILTER)
    assert attrs is attrs_cached
