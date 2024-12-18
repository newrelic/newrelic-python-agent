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

import pika
import pika.adapters
import pika.adapters.tornado_connection
import pytest
from testing_support.db_settings import rabbitmq_settings

from newrelic.hooks.messagebroker_pika import instance_info

DB_SETTINGS = rabbitmq_settings()[0]
EXPECTED_HOST = DB_SETTINGS["host"]
CONNECTION_PARAMS = [
    pika.ConnectionParameters(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"]),
    pika.URLParameters(f"amqp://{DB_SETTINGS['host']}:{DB_SETTINGS['port']}"),
]


@pytest.mark.parametrize("params", CONNECTION_PARAMS)
def test_instance_info_blocking_connection(params):
    with pika.BlockingConnection(params) as connection:
        channel = connection.channel()
        host = instance_info(channel)
        assert host == EXPECTED_HOST


@pytest.mark.parametrize("params", CONNECTION_PARAMS)
def test_instance_info_select_connection(params):
    _channel = []

    def on_open(connection):
        connection.channel(on_open_callback=on_channel_open)

    def on_channel_open(channel):
        _channel.append(channel)

        connection.close()
        connection.ioloop.stop()

    parameters = pika.ConnectionParameters(DB_SETTINGS["host"])
    connection = pika.SelectConnection(parameters=parameters, on_open_callback=on_open)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.start()
        raise

    channel = _channel.pop()
    host = instance_info(channel)
    assert host == EXPECTED_HOST


@pytest.mark.parametrize("params", CONNECTION_PARAMS)
def test_instance_info_tornado_connection(params):
    _channel = []

    def on_open(connection):
        connection.channel(on_open_callback=on_channel_open)

    def on_channel_open(channel):
        _channel.append(channel)

        connection.close()
        connection.ioloop.stop()

    parameters = pika.ConnectionParameters(DB_SETTINGS["host"])
    connection = pika.adapters.tornado_connection.TornadoConnection(parameters=parameters, on_open_callback=on_open)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.start()
        raise

    channel = _channel.pop()
    host = instance_info(channel)
    assert host == EXPECTED_HOST
