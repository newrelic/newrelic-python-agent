import pika
import pytest

from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
        capture_transaction_metrics)
from testing_support.settings import rabbitmq_settings

DB_SETTINGS = rabbitmq_settings()
QUEUE = 'test_pika_comsume'
BODY = 'test_body'


@pytest.fixture()
def producer():
    # put something into the queue so it can be consumed
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE)

        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
            body=BODY,
        )


_test_blocking_connection_basic_get_scoped_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]
_test_blocking_connection_basic_get_rollup_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]


@validate_transaction_metrics(
        'test_pika_consume:test_blocking_connection_basic_get',
        scoped_metrics=_test_blocking_connection_basic_get_scoped_metrics,
        rollup_metrics=_test_blocking_connection_basic_get_rollup_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_basic_get(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE)

        method_frame, _, _ = channel.basic_get(QUEUE)
        channel.basic_ack(method_frame.delivery_tag)
        assert method_frame


_test_blocking_connection_basic_consume_outside_transaction_scoped_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
    ('Function/test_pika_consume:on_message', 1),
]
_test_blocking_connection_basic_consume_outside_transaction_rollup_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]


@validate_transaction_metrics(
        'Named/None',  # TODO: Replace with destination type/name
        scoped_metrics=_test_blocking_connection_basic_consume_outside_transaction_scoped_metrics,
        rollup_metrics=_test_blocking_connection_basic_consume_outside_transaction_rollup_metrics,
        background_task=True,
        group='Message/RabbitMQ/None')
def test_blocking_connection_basic_consume_outside_transaction(producer):
    # The instrumentation for basic_consume will create the background_task
    # which is why this test does not have the background_task decorator

    metrics_list = []

    @capture_transaction_metrics(metrics_list)
    def test_blocking():
        def on_message(channel, method_frame, header_frame, body):
            assert body == BODY
            channel.stop_consuming()

        with pika.BlockingConnection(
                pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
            channel = connection.channel()
            channel.basic_consume(on_message, QUEUE)
            try:
                channel.start_consuming()
            except:
                channel.stop_consuming()
                raise

    test_blocking()

    # Make sure that metrics have been created. The
    # validate_transaction_metrics fixture won't run at all if they aren't.
    assert metrics_list


_test_blocking_connection_basic_consume_inside_transaction_scoped_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
    ('Function/test_pika_consume:on_message', 1),
]
_test_blocking_connection_basic_consume_inside_transaction_rollup_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]


@validate_transaction_metrics(
        'test_pika_consume:test_blocking_connection_basic_consume_inside_transaction',
        scoped_metrics=_test_blocking_connection_basic_consume_inside_transaction_scoped_metrics,
        rollup_metrics=_test_blocking_connection_basic_consume_inside_transaction_rollup_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_basic_consume_inside_transaction(producer):
    def on_message(channel, method_frame, header_frame, body):
        assert body == BODY
        channel.stop_consuming()

    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        channel.basic_consume(on_message, QUEUE)
        try:
            channel.start_consuming()
        except:
            channel.stop_consuming()
            raise


_test_blocking_connection_consume_scoped_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]
_test_blocking_connection_consume_rollup_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]


@validate_transaction_metrics(
        'test_pika_consume:test_blocking_connection_consume',
        scoped_metrics=_test_blocking_connection_consume_scoped_metrics,
        rollup_metrics=_test_blocking_connection_consume_rollup_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        for method_frame, properties, body in channel.consume(QUEUE):
            assert body == BODY
            break
