import newrelic.core.messagebroker_node

_ms_node = newrelic.core.messagebroker_node.MessageBrokerNode(
        product='RabbitMQ',
        target=None,
        operation='Consume',
        children=[],
        start_time=0.1,
        end_time=0.9,
        duration=0.8,
        exclusive=0.8,
        destination_type=None,
        destination_name=None,
        async=False)


def test_product_property():
    assert _ms_node.product == 'RabbitMQ'


def test_operation():
    assert _ms_node.operation == 'Consume'


def test_target():
    assert _ms_node.target is None


def test_destination_type():
    assert _ms_node.destination_type is None


def test_destination_name():
    assert _ms_node.destination_name is None
