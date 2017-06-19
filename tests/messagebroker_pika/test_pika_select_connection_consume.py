import pika
import pytest
import six
import uuid

from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
        capture_transaction_metrics)
from testing_support.settings import rabbitmq_settings

DB_SETTINGS = rabbitmq_settings()
QUEUE = 'test_pika_comsume-%s' % uuid.uuid4()
BODY = b'test_body'


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


_test_select_conn_basic_get_inside_txn_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]

if six.PY3:
    _test_select_conn_basic_get_inside_txn_metrics.append(
        (('Function/test_pika_select_connection_consume:'
          'test_select_connection_basic_get_inside_txn.'
          '<locals>.on_message'), 1))
else:
    _test_select_conn_basic_get_inside_txn_metrics.append(
        ('Function/test_pika_select_connection_consume:on_message', 1))


@validate_transaction_metrics(
        ('test_pika_select_connection_consume:'
                'test_select_connection_basic_get_inside_txn'),
        scoped_metrics=_test_select_conn_basic_get_inside_txn_metrics,
        rollup_metrics=_test_select_conn_basic_get_inside_txn_metrics,
        background_task=True)
@background_task()
def test_select_connection_basic_get_inside_txn(producer):
    def on_message(channel, method_frame, header_frame, body):
        assert method_frame
        assert body == BODY
        channel.close()
        connection.close()
        connection.ioloop.start()

    def on_open_channel(channel):
        channel.basic_get(callback=on_message, queue=QUEUE)

    def on_open_connection(connection):
        connection.channel(on_open_channel)

    connection = pika.SelectConnection(
            pika.ConnectionParameters(DB_SETTINGS['host']),
            on_open_callback=on_open_connection)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.start()
        raise


_test_select_conn_basic_get_outside_txn_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]

if six.PY3:
    _test_select_conn_basic_get_outside_txn_metrics.append(
        (('Function/test_pika_select_connection_consume:'
          'test_select_connection_basic_get_outside_txn.'
          '<locals>.test_basic_get.<locals>.on_message'), 1))
else:
    _test_select_conn_basic_get_outside_txn_metrics.append(
        ('Function/test_pika_select_connection_consume:on_message', 1))


@validate_transaction_metrics(
        'Named/None',  # TODO: Replace with destination type/name
        scoped_metrics=_test_select_conn_basic_get_outside_txn_metrics,
        rollup_metrics=_test_select_conn_basic_get_outside_txn_metrics,
        background_task=True,
        group='Message/RabbitMQ/None')
def test_select_connection_basic_get_outside_txn(producer):
    # The instrumentation for basic_consume will create the background_task
    # which is why this test does not have the background_task decorator

    metrics_list = []

    @capture_transaction_metrics(metrics_list)
    def test_basic_get():
        def on_message(channel, method_frame, header_frame, body):
            assert method_frame
            assert body == BODY
            channel.close()
            connection.close()
            connection.ioloop.start()

        def on_open_channel(channel):
            channel.basic_get(callback=on_message, queue=QUEUE)

        def on_open_connection(connection):
            connection.channel(on_open_channel)

        connection = pika.SelectConnection(
                pika.ConnectionParameters(DB_SETTINGS['host']),
                on_open_callback=on_open_connection)

        try:
            connection.ioloop.start()
        except:
            connection.close()
            # Start the IOLoop again so Pika can communicate, it will stop on
            # its own when the connection is closed
            connection.ioloop.start()
            raise

    test_basic_get()

    # Make sure that metrics have been created. The
    # validate_transaction_metrics fixture won't run at all if they aren't.
    assert metrics_list


_test_select_conn_basic_get_inside_txn_no_callback_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]


@validate_transaction_metrics(
    ('test_pika_select_connection_consume:'
            'test_select_connection_basic_get_inside_txn_no_callback'),
    scoped_metrics=_test_select_conn_basic_get_inside_txn_no_callback_metrics,
    rollup_metrics=_test_select_conn_basic_get_inside_txn_no_callback_metrics,
    background_task=True)
@background_task()
def test_select_connection_basic_get_inside_txn_no_callback(producer):
    def on_open_channel(channel):
        channel.basic_get(callback=None, queue=QUEUE)
        channel.close()
        connection.close()
        connection.ioloop.start()

    def on_open_connection(connection):
        connection.channel(on_open_channel)

    connection = pika.SelectConnection(
            pika.ConnectionParameters(DB_SETTINGS['host']),
            on_open_callback=on_open_connection)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.start()
        raise


_test_select_conn_basic_consume_in_txn_metrics = [
    ('MessageBroker/RabbitMQ/None/Produce/Named/None', None),
    ('MessageBroker/RabbitMQ/None/Consume/Named/None', None),
]

if six.PY3:
    _test_select_conn_basic_consume_in_txn_metrics.append(
        (('Function/test_pika_select_connection_consume:'
          'test_select_connection_basic_consume_inside_txn.'
          '<locals>.on_message'), 1))
else:
    _test_select_conn_basic_consume_in_txn_metrics.append(
        ('Function/test_pika_select_connection_consume:on_message', 1))


@validate_transaction_metrics(
        ('test_pika_select_connection_consume:'
                'test_select_connection_basic_consume_inside_txn'),
        scoped_metrics=_test_select_conn_basic_consume_in_txn_metrics,
        rollup_metrics=_test_select_conn_basic_consume_in_txn_metrics,
        background_task=True)
@background_task()
def test_select_connection_basic_consume_inside_txn(producer):
    def on_message(channel, method_frame, header_frame, body):
        assert hasattr(method_frame, '_nr_start_time')
        assert body == BODY
        channel.close()
        connection.close()
        connection.ioloop.start()

    def on_open_channel(channel):
        channel.basic_consume(on_message, QUEUE)

    def on_open_connection(connection):
        connection.channel(on_open_channel)

    connection = pika.SelectConnection(
            pika.ConnectionParameters(DB_SETTINGS['host']),
            on_open_callback=on_open_connection)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.start()
        raise
