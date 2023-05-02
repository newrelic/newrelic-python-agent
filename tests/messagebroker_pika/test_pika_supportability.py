# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from compat import basic_consume
import pika
import six

from newrelic.api.background_task import background_task

from conftest import QUEUE, BODY
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.db_settings import rabbitmq_settings

DB_SETTINGS = rabbitmq_settings()[0]


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
        connection.ioloop.stop()

    def on_open_channel(channel):
        channel.basic_get(callback=on_message, queue=QUEUE)

    def on_open_connection(connection):
        connection.channel(on_open_callback=on_open_channel)

    connection = CustomPikaConnection(
            pika.ConnectionParameters(DB_SETTINGS['host']),
            on_open_callback=on_open_connection)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.stop()
        raise


if six.PY3:
    _txn_name = ('test_pika_supportability:'
            'test_select_connection_supportability_outside_txn.'
            '<locals>.on_message')
else:
    _txn_name = (
        'test_pika_supportability:on_message')


@validate_transaction_metrics(
        _txn_name,
        scoped_metrics=(),
        rollup_metrics=_test_select_connection_supportability_metrics,
        background_task=True,
        group='Message/RabbitMQ/Exchange/Unknown')
def test_select_connection_supportability_outside_txn(producer):
    def on_message(channel, method_frame, header_frame, body):
        assert method_frame
        assert body == BODY
        channel.basic_ack(method_frame.delivery_tag)
        channel.close()
        connection.close()
        connection.ioloop.stop()

    def on_open_channel(channel):
        basic_consume(channel, QUEUE, on_message)

    def on_open_connection(connection):
        connection.channel(on_open_callback=on_open_channel)

    connection = CustomPikaConnection(
            pika.ConnectionParameters(DB_SETTINGS['host']),
            on_open_callback=on_open_connection)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.stop()
        raise
