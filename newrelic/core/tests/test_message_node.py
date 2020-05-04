import newrelic.core.message_node
from newrelic.core.config import global_settings_dump
from newrelic.core.attribute_filter import AttributeFilter


class DummySettings(object):
    attribute_filter = AttributeFilter(global_settings_dump())


_ms_node = newrelic.core.message_node.MessageNode(
        library='RabbitMQ',
        operation='Consume',
        children=[],
        start_time=0.1,
        end_time=0.9,
        duration=0.8,
        exclusive=0.8,
        destination_type=None,
        destination_name=None,
        params={'hello': True},
        guid=None,
        agent_attributes={},
        user_attributes={},
)


def test_library_property():
    assert _ms_node.library == 'RabbitMQ'


def test_operation():
    assert _ms_node.operation == 'Consume'


def test_destination_type():
    assert _ms_node.destination_type is None


def test_destination_name():
    assert _ms_node.destination_name is None


def test_params():
    assert _ms_node.params == {'hello': True}


def test_trace_node_uses_params():
    class DummyCache(object):
        @staticmethod
        def cache(name):
            pass

    class DummyRoot(object):
        trace_node_count = 0
        string_table = DummyCache
        start_time = 0.0
        end_time = 0.0
        settings = DummySettings

    trace_node = _ms_node.trace_node(None, DummyRoot, None)
    assert trace_node.params['hello'] is True, trace_node.params
