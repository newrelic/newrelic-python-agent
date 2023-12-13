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

from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture  # noqa: F401; pylint: disable=W0611

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import transient_function_wrapper

DB_SETTINGS = kafka_settings()[0]

BROKER = "%s:%s" % (DB_SETTINGS["host"], DB_SETTINGS["port"])


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


@pytest.fixture(scope="session", params=["cimpl", "serializer_function", "serializer_object"])
def client_type(request):
    return request.param


@pytest.fixture()
def skip_if_not_serializing(client_type):
    if client_type == "cimpl":
        pytest.skip("Only serializing clients supported.")


@pytest.fixture(scope="function")
def producer(topic, client_type, json_serializer):
    from confluent_kafka import Producer, SerializingProducer

    if client_type == "cimpl":
        producer = Producer({"bootstrap.servers": BROKER})
    elif client_type == "serializer_function":
        producer = SerializingProducer(
            {
                "bootstrap.servers": BROKER,
                "value.serializer": lambda v, c: json.dumps(v).encode("utf-8"),
                "key.serializer": lambda v, c: json.dumps(v).encode("utf-8") if v is not None else None,
            }
        )
    elif client_type == "serializer_object":
        producer = SerializingProducer(
            {
                "bootstrap.servers": BROKER,
                "value.serializer": json_serializer,
                "key.serializer": json_serializer,
            }
        )

    yield producer

    if hasattr(producer, "purge"):
        producer.purge()


@pytest.fixture(scope="function")
def consumer(group_id, topic, producer, client_type, json_deserializer):
    from confluent_kafka import Consumer, DeserializingConsumer

    if client_type == "cimpl":
        consumer = Consumer(
            {
                "bootstrap.servers": BROKER,
                "auto.offset.reset": "earliest",
                "heartbeat.interval.ms": 1000,
                "group.id": group_id,
            }
        )
    elif client_type == "serializer_function":
        consumer = DeserializingConsumer(
            {
                "bootstrap.servers": BROKER,
                "auto.offset.reset": "earliest",
                "heartbeat.interval.ms": 1000,
                "group.id": group_id,
                "value.deserializer": lambda v, c: json.loads(v.decode("utf-8")),
                "key.deserializer": lambda v, c: json.loads(v.decode("utf-8")) if v is not None else None,
            }
        )
    elif client_type == "serializer_object":
        consumer = DeserializingConsumer(
            {
                "bootstrap.servers": BROKER,
                "auto.offset.reset": "earliest",
                "heartbeat.interval.ms": 1000,
                "group.id": group_id,
                "value.deserializer": json_deserializer,
                "key.deserializer": json_deserializer,
            }
        )

    consumer.subscribe([topic])

    yield consumer

    consumer.close()


@pytest.fixture(scope="session")
def serialize(client_type):
    if client_type == "cimpl":
        return lambda v: json.dumps(v).encode("utf-8")
    else:
        return lambda v: v


@pytest.fixture(scope="session")
def deserialize(client_type):
    if client_type == "cimpl":
        return lambda v: json.loads(v.decode("utf-8"))
    else:
        return lambda v: v


@pytest.fixture(scope="session")
def json_serializer():
    from confluent_kafka.serialization import Serializer

    class JSONSerializer(Serializer):
        def __call__(self, obj, ctx):
            return json.dumps(obj).encode("utf-8") if obj is not None else None

    return JSONSerializer()


@pytest.fixture(scope="session")
def json_deserializer():
    from confluent_kafka.serialization import Deserializer

    class JSONDeserializer(Deserializer):
        def __call__(self, obj, ctx):
            return json.loads(obj.decode("utf-8")) if obj is not None else None

    return JSONDeserializer()


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


@pytest.fixture(scope="session")
def group_id():
    return str(uuid.uuid4())


@pytest.fixture()
def send_producer_message(topic, producer, serialize, client_type):
    callback_called = []

    def producer_callback(err, msg):
        callback_called.append(True)

    def _test():
        if client_type == "cimpl":
            producer.produce(topic, value=serialize({"foo": 1}), callback=producer_callback)
        else:
            producer.produce(topic, value=serialize({"foo": 1}), on_delivery=producer_callback)
        producer.flush()
        assert callback_called

    return _test


@pytest.fixture()
def get_consumer_record(topic, send_producer_message, consumer, deserialize):
    def _test():
        send_producer_message()

        record_count = 0

        timeout = 10
        attempts = 0
        record = None
        while not record and attempts < timeout:
            record = consumer.poll(0.5)
            if not record:
                attempts += 1
                continue
            assert not record.error()

            assert deserialize(record.value()) == {"foo": 1}
            record_count += 1
        consumer.poll(0.5)  # Exit the transaction.

        assert record_count == 1, "Incorrect count of records consumed: %d. Expected 1." % record_count

    return _test


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
