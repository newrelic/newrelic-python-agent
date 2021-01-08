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
import pytest
import uuid

from testing_support.db_settings import rabbitmq_settings
from testing_support.fixtures import (code_coverage_fixture,  # NOQA
        collector_agent_registration_fixture, collector_available_fixture)


QUEUE = 'test_pika-%s' % uuid.uuid4()
QUEUE_2 = 'test_pika-%s' % uuid.uuid4()

EXCHANGE = 'exchange-%s' % uuid.uuid4()
EXCHANGE_2 = 'exchange-%s' % uuid.uuid4()

CORRELATION_ID = 'test-correlation-id'
REPLY_TO = 'test-reply-to'
HEADERS = {'TestHeader': 'my test header value'}
BODY = b'test_body'

DB_SETTINGS = rabbitmq_settings()[0]

_coverage_source = [
    'newrelic.hooks.messagebroker_pika',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (messagebroker_pika)',
        default_settings=_default_settings,
        linked_applications=['Python Agent Test (messagebroker)'])


@pytest.fixture()
def producer():
    # put something into the queue so it can be consumed
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        channel.queue_declare(queue=QUEUE, durable=False)
        channel.exchange_declare(exchange=EXCHANGE, durable=False)
        channel.queue_bind(queue=QUEUE, exchange=EXCHANGE)

        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=QUEUE,
            body=BODY,
            properties=pika.spec.BasicProperties(
                correlation_id=CORRELATION_ID,
                reply_to=REPLY_TO,
                headers=HEADERS),
        )
        yield
        channel.queue_delete(queue=QUEUE)
        channel.exchange_delete(exchange=EXCHANGE)


@pytest.fixture()
def producer_2():
    # put something into the queue so it can be consumed
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        channel.queue_declare(queue=QUEUE_2, durable=False)
        channel.exchange_declare(exchange=EXCHANGE_2, durable=False)
        channel.queue_bind(queue=QUEUE_2, exchange=EXCHANGE_2)

        channel.basic_publish(
            exchange=EXCHANGE_2,
            routing_key=QUEUE_2,
            body=BODY,
            properties=pika.spec.BasicProperties(
                correlation_id=CORRELATION_ID,
                reply_to=REPLY_TO,
                headers=HEADERS),
        )
        yield
        channel.queue_delete(queue=QUEUE_2)
        channel.exchange_delete(exchange=EXCHANGE_2)


@pytest.fixture()
def produce_five():
    # put something into the queue so it can be consumed
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        channel.queue_declare(queue=QUEUE, durable=False)
        channel.exchange_declare(exchange=EXCHANGE, durable=False)
        channel.queue_bind(queue=QUEUE, exchange=EXCHANGE)

        for _ in range(5):
            channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=QUEUE,
                body=BODY,
                properties=pika.spec.BasicProperties(
                    correlation_id=CORRELATION_ID,
                    reply_to=REPLY_TO,
                    headers=HEADERS),
            )

        yield
        channel.queue_delete(queue=QUEUE)
        channel.exchange_delete(exchange=EXCHANGE)
