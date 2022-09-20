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

import pytest
from testing_support.db_settings import kafka_settings
from testing_support.fixtures import (  # noqa: F401, W0611
    code_coverage_fixture,
    collector_agent_registration_fixture,
    collector_available_fixture,
)

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import transient_function_wrapper

DB_SETTINGS = kafka_settings()[0]

BROKER = "%s:%s" % (DB_SETTINGS["host"], DB_SETTINGS["port"])

_coverage_source = [
    "newrelic.hooks.messagebroker_confluentkafka",
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (messagebroker_confluentkafka)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (messagebroker_confluentkafka)"],
)


@pytest.fixture(scope="function")
def producer_cimpl():
    from confluent_kafka import Producer

    return Producer(
        {
            "bootstrap.servers": BROKER,
        }
    )


@pytest.fixture(scope="function")
def producer_serializing():
    from confluent_kafka import SerializingProducer

    return SerializingProducer(
        {
            "bootstrap.servers": BROKER,
            "value.serializer": lambda v, c: json.dumps(v).encode("utf-8"),
            "key.serializer": lambda v, c: v.encode("utf-8") if v is not None else None,
        }
    )


@pytest.fixture(scope="function", params=["cimpl", "serializing"])
def producer(request, producer_cimpl, producer_serializing):
    if request.param == "cimpl":
        producer = producer_cimpl
    elif request.param == "serializing":
        producer = producer_serializing
    yield producer


@pytest.fixture(scope="function")
def consumer_cimpl(topic, producer_cimpl):
    from confluent_kafka import Consumer

    consumer_config = {
        "bootstrap.servers": BROKER,
        "auto.offset.reset": "earliest",
        "heartbeat.interval.ms": 1000,
        "group.id": "test",
    }

    return Consumer(consumer_config)


@pytest.fixture(scope="function")
def consumer_deserializing(topic, producer_serializing):
    from confluent_kafka import DeserializingConsumer

    consumer_config = {
        "bootstrap.servers": BROKER,
        "auto.offset.reset": "earliest",
        "heartbeat.interval.ms": 1000,
        "group.id": "test",
        "value.deserializer": lambda v, c: json.loads(v.decode("utf-8")),
        "key.deserializer": lambda v, c: v.decode("utf-8") if v is not None else None,
    }

    return DeserializingConsumer(consumer_config)


@pytest.fixture(scope="function")
def consumer(topic, producer, consumer_cimpl, consumer_deserializing):
    from confluent_kafka import SerializingProducer

    if isinstance(producer, SerializingProducer):
        consumer = consumer_deserializing
    else:
        consumer = consumer_cimpl

    consumer.subscribe([topic])

    # The first time the kafka consumer is created and polled, it returns None.
    # To by-pass this, loop over the consumer before using it.
    # NOTE: This seems to only happen in Python2.7.
    while True:
        record = consumer.poll(0.5)
        if not record:
            break
        assert not record.error()

    yield consumer
    consumer.close()


@pytest.fixture(scope="function")
def serialize(producer):
    from confluent_kafka import SerializingProducer

    if isinstance(producer, SerializingProducer):
        return lambda v: v
    else:
        return lambda v: json.dumps(v).encode("utf-8")


@pytest.fixture(scope="function")
def deserialize(consumer):
    from confluent_kafka import DeserializingConsumer

    if isinstance(consumer, DeserializingConsumer):
        return lambda v: v
    else:
        return lambda v: json.loads(v.decode("utf-8"))


@pytest.fixture(scope="function")
def topic():
    from confluent_kafka.admin import AdminClient, NewTopic

    topic = "test-topic-%s" % str(uuid.uuid4())

    admin = AdminClient({"bootstrap.servers": BROKER})
    new_topics = [NewTopic(topic, num_partitions=1, replication_factor=1)]
    topics = admin.create_topics(new_topics)
    for _, f in topics.items():
        f.result()  # Block until topic is created.

    yield topic

    admin.delete_topics(new_topics)


def cache_kafka_producer_headers():
    import confluent_kafka.cimpl

    @transient_function_wrapper(confluent_kafka.cimpl, "Producer.produce.__wrapped__")
    # Place transient wrapper underneath instrumentation
    def _cache_kafka_producer_headers(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        ret = wrapped(*args, **kwargs)
        headers = kwargs.get("headers", [])
        headers = dict(headers)
        transaction._test_request_headers = headers
        return ret

    return _cache_kafka_producer_headers


def cache_kafka_consumer_headers():
    import confluent_kafka.cimpl

    @transient_function_wrapper(confluent_kafka.cimpl, "Consumer.poll")
    # Place transient wrapper underneath instrumentation
    def _cache_kafka_consumer_headers(wrapped, instance, args, kwargs):
        record = wrapped(*args, **kwargs)
        transaction = current_transaction()

        if transaction is None:
            return record

        headers = dict(record.headers())
        transaction._test_request_headers = headers
        return record

    return _cache_kafka_consumer_headers


@pytest.fixture(autouse=True)
def assert_no_active_transaction():
    # Run before test
    assert not current_transaction(active_only=False), "Transaction exists before test run."

    yield  # Run test

    # Run after test
    assert not current_transaction(active_only=False), "Transaction was not properly exited."
