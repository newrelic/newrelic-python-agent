import pika

from newrelic.api.background_task import background_task

from conftest import QUEUE
from testing_support.fixtures import validate_transaction_metrics
from testing_support.external_fixtures import validate_messagebroker_headers
from testing_support.settings import rabbitmq_settings
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import transient_function_wrapper


@transient_function_wrapper(pika.frame, 'Header.__init__')
def cache_pika_headers(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    ret = wrapped(*args, **kwargs)
    headers = instance.properties.headers
    transaction._test_request_headers = headers
    return ret


DB_SETTINGS = rabbitmq_settings()


_test_blocking_connection_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', 2),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection',
        scoped_metrics=_test_blocking_connection_metrics,
        rollup_metrics=_test_blocking_connection_metrics,
        background_task=True)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_blocking_connection(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        channel.basic_publish(
            exchange='',
            routing_key='hello',
            body='test',
        )

        channel.publish(
            exchange='',
            routing_key='hello',
            body='test',
        )


_test_blocking_connection_two_exchanges_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/exchange_1', 1),
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/exchange_2', 1),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/exchange_1', None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/exchange_2', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection_two_exchanges',
        scoped_metrics=_test_blocking_connection_two_exchanges_metrics,
        rollup_metrics=_test_blocking_connection_two_exchanges_metrics,
        background_task=True)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_blocking_connection_two_exchanges():
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        channel.queue_declare(queue='hello')
        channel.exchange_declare(exchange='exchange_1', durable=False,
                auto_delete=True)
        channel.exchange_declare(exchange='exchange_2', durable=False,
                auto_delete=True)

        channel.basic_publish(
            exchange='exchange_1',
            routing_key='hello',
            body='test',
        )
        channel.basic_publish(
            exchange='exchange_2',
            routing_key='hello',
            body='test',
        )


_test_select_connection_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', 1),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_select_connection',
        scoped_metrics=_test_select_connection_metrics,
        rollup_metrics=_test_select_connection_metrics,
        background_task=True)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_select_connection():
    def on_open(connection):
        connection.channel(on_channel_open)

    def on_channel_open(channel):
        channel.basic_publish(
            exchange='',
            routing_key='hello',
            body='test',
        )
        connection.close()

    parameters = pika.ConnectionParameters(DB_SETTINGS['host'])
    connection = pika.SelectConnection(
            parameters=parameters,
            on_open_callback=on_open)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.start()
        raise


_test_tornado_connection_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', 1),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_tornado_connection',
        scoped_metrics=_test_tornado_connection_metrics,
        rollup_metrics=_test_tornado_connection_metrics,
        background_task=True)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_tornado_connection():
    def on_open(connection):
        connection.channel(on_channel_open)

    def on_channel_open(channel):
        channel.basic_publish(
            exchange='',
            routing_key='hello',
            body='test',
        )
        connection.close()
        connection.ioloop.stop()

    parameters = pika.ConnectionParameters(DB_SETTINGS['host'])
    connection = pika.TornadoConnection(
            parameters=parameters,
            on_open_callback=on_open)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.start()
        raise
