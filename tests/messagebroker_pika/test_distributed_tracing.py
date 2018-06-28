import pika
import six

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

from testing_support.settings import rabbitmq_settings
from testing_support.fixtures import (override_application_settings,
        validate_transaction_metrics)

DB_SETTINGS = rabbitmq_settings()

_override_settings = {
    'account_id': '332029',
    'trusted_account_ids': ['1', '332029'],
    'trusted_account_key': '1',
    'cross_application_tracer.enabled': True,
    'feature_flag': set(['distributed_tracing']),
}

_test_distributed_tracing_basic_publish_metrics = [
    ('DurationByCaller/Unknown/Unknown/Unknown/Unknown/allOther', 1),
]


@validate_transaction_metrics(
        'test_distributed_tracing:do_basic_publish',
        rollup_metrics=_test_distributed_tracing_basic_publish_metrics,
        background_task=True)
@background_task()
def do_basic_publish(channel, QUEUE, properties=None):
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE,
        body='Testing distributed_tracing 123',
        properties=properties,
    )


_test_distributed_tracing_basic_consume_rollup_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', None),
]

if six.PY3:
    _consume_txn_name = ('test_distributed_tracing:'
            'test_basic_consume_distributed_tracing_headers.'
            '<locals>.on_receive')
else:
    _consume_txn_name = (
        'test_distributed_tracing:on_receive')


@validate_transaction_metrics(
        _consume_txn_name,
        rollup_metrics=_test_distributed_tracing_basic_consume_rollup_metrics,
        background_task=True,
        group='Message/RabbitMQ/Exchange/Default')
def do_basic_consume(channel):
    channel.start_consuming()


@override_application_settings(_override_settings)
def test_basic_consume_distributed_tracing_headers():
    def on_receive(ch, method, properties, msg):
        headers = properties.headers
        assert headers
        assert 'NewRelicID' not in headers
        assert 'NewRelicTransaction' not in headers
        assert msg == b'Testing distributed_tracing 123'
        txn = current_transaction()

        assert txn
        assert txn.is_distributed_trace
        assert txn.parent_type == 'App'
        assert txn.parent_tx == txn._trace_id
        assert txn.parent_span is None
        assert txn.parent_account == txn.settings.account_id
        assert txn.parent_transport_type == 'HTTP'
        assert txn._priority is not None
        assert txn._sampled is not None

        ch.stop_consuming()

    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        channel.queue_declare('TESTDT', durable=False)

        properties = pika.BasicProperties()
        properties.headers = {'Hello': 'World'}

        try:
            channel.basic_consume(on_receive,
                no_ack=True,
                queue='TESTDT')
            do_basic_publish(channel, 'TESTDT', properties=properties)
            do_basic_consume(channel)

        finally:
            channel.queue_delete('TESTDT')


_test_distributed_tracing_basic_get_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', 1),
    ('DurationByCaller/Unknown/Unknown/Unknown/Unknown/allOther', 1),
]


@validate_transaction_metrics(
        'test_distributed_tracing:do_basic_get',
        rollup_metrics=_test_distributed_tracing_basic_get_metrics,
        background_task=True)
@background_task()
def do_basic_get(channel, QUEUE):
    _, properties, msg = channel.basic_get(QUEUE)
    headers = properties.headers

    assert headers
    assert 'NewRelicID' not in headers
    assert 'NewRelicTransaction' not in headers
    assert msg == b'Testing distributed_tracing 123'

    txn = current_transaction()

    assert txn.client_cross_process_id is None
    assert txn.client_account_id is None
    assert txn.client_application_id is None


@override_application_settings(_override_settings)
def test_basic_get_no_distributed_tracing_headers():
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        channel.queue_declare('TESTDT', durable=False)

        properties = pika.BasicProperties()
        properties.headers = {'Hello': 'World'}

        try:
            do_basic_publish(channel, 'TESTDT', properties=properties)
            do_basic_get(channel, 'TESTDT')
        finally:
            channel.queue_delete('TESTDT')
