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

import json
import uuid
import pickle

import kombu
import pytest
from kombu import messaging
from kombu import serialization
from testing_support.db_settings import rabbitmq_settings
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)
from testing_support.validators.validate_distributed_trace_accepted import validate_distributed_trace_accepted

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import transient_function_wrapper

TRANSPORT_TYPES = {"pyamqp": "AMQP", "amqp": "AMQP"}
DB_SETTINGS = rabbitmq_settings()[0]


@pytest.fixture(
    scope="session",
    params=[
        "pyamqp"  # , "amqp", #"qpid", "redis"
    ],
)
def transport_type(request):
    return request.param


@pytest.fixture(scope="session")
def producer_connection(transport_type):
    host = DB_SETTINGS["host"]
    with kombu.Connection(f"{transport_type}://{host}") as conn:
        yield conn


@pytest.fixture(scope="session")
def consumer_connection(transport_type):
    with kombu.Connection(DB_SETTINGS["host"]) as conn:
        yield conn


_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "kombu.consumer.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (messagebroker_kombu)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (messagebroker_kombu)"],
)


@pytest.fixture(scope="function")
def producer(producer_connection):
    # Purge the queue.
    channel = producer_connection.channel()
    channel.queue_purge("bar")

    producer = producer_connection.Producer(serializer="json")

    yield producer


@pytest.fixture(scope="function")
def consumer(producer, consumer_connection, queue, consume):
    # According to the docs:
    #   Note that a Consumer does not need the serialization method specified. They can
    #   auto-detect the serialization method as the content-type is sent as a message
    #   header.
    consumer = consumer_connection.Consumer(queue, callbacks=[consume])
    with consumer as con:
        yield con


@pytest.fixture(scope="function")
def consumer_callback_error(producer, consumer_connection, queue, consume_error):
    consumer = consumer_connection.Consumer(queue, callbacks=[consume_error])
    with consumer as con:
        yield con


@pytest.fixture(scope="function")
def consumer_validate_dt(producer, consumer_connection, queue, consume_validate_dt):
    consumer = consumer_connection.Consumer(queue, callbacks=[consume_validate_dt])
    with consumer as con:
        yield con


@pytest.fixture
def consume(events):
    def _consume(body, message):
        message.ack()
        events.append({"body": body, "routing_key": message.delivery_info["routing_key"]})

    return _consume


@pytest.fixture
def consume_error(events):
    def _consume(body, message):
        message.ack()
        events.append({"body": body, "routing_key": message.delivery_info["routing_key"]})
        raise RuntimeError("Error in consumer callback")

    return _consume


@pytest.fixture
def consume_validate_dt(events, transport_type):
    expected_transport_type = TRANSPORT_TYPES[transport_type]

    @validate_distributed_trace_accepted(transport_type=expected_transport_type)
    def _consume(body, message):
        # Capture headers to validate dt headers.
        txn = current_transaction()
        txn._test_request_headers = message.headers

        message.ack()
        events.append({"body": body, "routing_key": message.delivery_info["routing_key"]})

    return _consume


@pytest.fixture
def events():
    return []


@pytest.fixture
def exchange():
    return kombu.Exchange("exchange", "direct", durable=True)


@pytest.fixture
def queue(exchange):
    return kombu.Queue("bar", exchange=exchange, routing_key="bar")


@pytest.fixture
def send_producer_message(producer, exchange, queue):
    def _test():
        producer.publish({"foo": 1}, exchange=exchange, routing_key="bar", declare=[queue])

    return _test


@pytest.fixture
def get_consumer_record(send_producer_message, consumer_connection, consumer):
    def _test():
        send_producer_message()

        consumer_connection.drain_events(timeout=5)

    return _test


@pytest.fixture
def get_consumer_record_error(send_producer_message, consumer_connection, consumer_callback_error):
    def _test():
        send_producer_message()

        consumer_connection.drain_events(timeout=5)

    return _test


@transient_function_wrapper(messaging, "Producer.publish.__wrapped__")
# Place transient wrapper underneath instrumentation
def cache_kombu_producer_headers(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    ret = wrapped(*args, **kwargs)

    headers = kwargs.get("headers", [])
    transaction._test_request_headers = headers
    return ret
