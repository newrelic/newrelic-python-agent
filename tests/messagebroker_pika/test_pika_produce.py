import pika

from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
        validate_tt_collector_json)
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
QUEUE = 'cats-are-better-than-dogs'

_message_broker_tt_included_params = {
    'routing_key': QUEUE,
}

_message_broker_tt_forgone_params = ['queue_name']

_test_blocking_connection_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', 2),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection',
        scoped_metrics=_test_blocking_connection_metrics,
        rollup_metrics=_test_blocking_connection_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_params,
        message_broker_forgone_params=_message_broker_tt_forgone_params)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_blocking_connection(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
        )

        channel.publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
        )


_test_blocking_connection_two_exchanges_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/exchange-1', 1),
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/exchange-2', 1),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/exchange-1', None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/exchange-2', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection_two_exchanges',
        scoped_metrics=_test_blocking_connection_two_exchanges_metrics,
        rollup_metrics=_test_blocking_connection_two_exchanges_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_params,
        message_broker_forgone_params=_message_broker_tt_forgone_params)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_blocking_connection_two_exchanges():
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE)
        channel.exchange_declare(exchange='exchange-1', durable=False,
                auto_delete=True)
        channel.exchange_declare(exchange='exchange-2', durable=False,
                auto_delete=True)

        channel.basic_publish(
            exchange='exchange-1',
            routing_key=QUEUE,
            body='test',
        )
        channel.basic_publish(
            exchange='exchange-2',
            routing_key=QUEUE,
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
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_params,
        message_broker_forgone_params=_message_broker_tt_forgone_params)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_select_connection():
    def on_open(connection):
        connection.channel(on_channel_open)

    def on_channel_open(channel):
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
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
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_params,
        message_broker_forgone_params=_message_broker_tt_forgone_params)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_tornado_connection():
    def on_open(connection):
        connection.channel(on_channel_open)

    def on_channel_open(channel):
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
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
