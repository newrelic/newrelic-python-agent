import pika
import pytest
import uuid

from newrelic.api.background_task import background_task

from testing_support.fixtures import validate_transaction_metrics
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
        yield
        channel.queue_purge(queue=QUEUE)


class CustomPikaChannel(pika.channel.Channel):
    def _on_getok(self, method_frame, header_frame, body):
        if self._on_getok_callback is not None:
            callback = self._on_getok_callback
            self._on_getok_callback = None
            # Use kwargs to pass values to callback
            callback(channel=self,
                    method_frame=method_frame.method,
                    header_frame=header_frame.properties,
                    body=body)

    def _on_deliver(self, method_frame, header_frame, body):
        consumer_tag = method_frame.method.consumer_tag

        if consumer_tag in self._cancelled:
            if self.is_open and consumer_tag not in self._consumers_with_noack:
                self.basic_reject(method_frame.method.delivery_tag)
            return

        self._consumers[consumer_tag](channel=self,
                method_frame=method_frame.method,
                header_frame=header_frame.properties,
                body=body)


class CustomPikaConnection(pika.SelectConnection):
    def _create_channel(self, channel_number, on_open_callback):
        return CustomPikaChannel(self, channel_number, on_open_callback)


_test_select_connection_supportability_metrics = [
    ('Supportability/hooks/pika/kwargs_error', 1)
]


@validate_transaction_metrics(
        ('test_pika_supportability:'
                'test_select_connection_supportability_in_txn'),
        scoped_metrics=(),
        rollup_metrics=_test_select_connection_supportability_metrics,
        background_task=True)
@background_task()
def test_select_connection_supportability_in_txn(producer):
    def on_message(channel, method_frame, header_frame, body):
        assert method_frame
        assert body == BODY
        channel.basic_ack(method_frame.delivery_tag)
        channel.close()
        connection.close()
        connection.ioloop.start()

    def on_open_channel(channel):
        channel.basic_get(callback=on_message, queue=QUEUE)

    def on_open_connection(connection):
        connection.channel(on_open_channel)

    connection = CustomPikaConnection(
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


@validate_transaction_metrics(
        'Named/None',  # TODO: Replace with destination type/name
        scoped_metrics=(),
        rollup_metrics=_test_select_connection_supportability_metrics,
        background_task=True,
        group='Message/RabbitMQ/None')
def test_select_connection_supportability_outside_txn(producer):
    def on_message(channel, method_frame, header_frame, body):
        assert method_frame
        assert body == BODY
        channel.basic_ack(method_frame.delivery_tag)
        channel.close()
        connection.close()
        connection.ioloop.start()

    def on_open_channel(channel):
        channel.basic_consume(on_message, QUEUE)

    def on_open_connection(connection):
        connection.channel(on_open_channel)

    connection = CustomPikaConnection(
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
