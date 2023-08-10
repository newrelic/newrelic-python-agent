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

import kafka
import pytest
from testing_support.db_settings import kafka_settings

from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture  # noqa: F401; pylint: disable=W0611

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import transient_function_wrapper

DB_SETTINGS = kafka_settings()[0]

BOOTSTRAP_SERVER = "%s:%s" % (DB_SETTINGS["host"], DB_SETTINGS["port"])
BROKER = [BOOTSTRAP_SERVER]


_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (messagebroker_kafkapython)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (messagebroker_kafkapython)"],
)


@pytest.fixture(
    scope="session", params=["no_serializer", "serializer_function", "callable_object", "serializer_object"]
)
def client_type(request):
    return request.param


@pytest.fixture()
def skip_if_not_serializing(client_type):
    if client_type == "no_serializer":
        pytest.skip("Only serializing clients supported.")


@pytest.fixture(scope="function")
def producer(client_type, json_serializer, json_callable_serializer):
    if client_type == "no_serializer":
        producer = kafka.KafkaProducer(bootstrap_servers=BROKER)
    elif client_type == "serializer_function":
        producer = kafka.KafkaProducer(
            bootstrap_servers=BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8") if v else None,
            key_serializer=lambda v: json.dumps(v).encode("utf-8") if v else None,
        )
    elif client_type == "callable_object":
        producer = kafka.KafkaProducer(
            bootstrap_servers=BROKER,
            value_serializer=json_callable_serializer,
            key_serializer=json_callable_serializer,
        )
    elif client_type == "serializer_object":
        producer = kafka.KafkaProducer(
            bootstrap_servers=BROKER,
            value_serializer=json_serializer,
            key_serializer=json_serializer,
        )

    yield producer
    producer.close()


@pytest.fixture(scope="function")
def consumer(group_id, topic, producer, client_type, json_deserializer, json_callable_deserializer):
    if client_type == "no_serializer":
        consumer = kafka.KafkaConsumer(
            topic,
            bootstrap_servers=BROKER,
            auto_offset_reset="earliest",
            consumer_timeout_ms=100,
            heartbeat_interval_ms=1000,
            group_id=group_id,
        )
    elif client_type == "serializer_function":
        consumer = kafka.KafkaConsumer(
            topic,
            bootstrap_servers=BROKER,
            key_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
            auto_offset_reset="earliest",
            consumer_timeout_ms=100,
            heartbeat_interval_ms=1000,
            group_id=group_id,
        )
    elif client_type == "callable_object":
        consumer = kafka.KafkaConsumer(
            topic,
            bootstrap_servers=BROKER,
            key_deserializer=json_callable_deserializer,
            value_deserializer=json_callable_deserializer,
            auto_offset_reset="earliest",
            consumer_timeout_ms=100,
            heartbeat_interval_ms=1000,
            group_id=group_id,
        )
    elif client_type == "serializer_object":
        consumer = kafka.KafkaConsumer(
            topic,
            bootstrap_servers=BROKER,
            key_deserializer=json_deserializer,
            value_deserializer=json_deserializer,
            auto_offset_reset="earliest",
            consumer_timeout_ms=100,
            heartbeat_interval_ms=1000,
            group_id=group_id,
        )

    yield consumer
    consumer.close()


@pytest.fixture(scope="session")
def serialize(client_type):
    if client_type == "no_serializer":
        return lambda v: json.dumps(v).encode("utf-8")
    else:
        return lambda v: v


@pytest.fixture(scope="session")
def deserialize(client_type):
    if client_type == "no_serializer":
        return lambda v: json.loads(v.decode("utf-8"))
    else:
        return lambda v: v


@pytest.fixture(scope="session")
def json_serializer():
    class JSONSerializer(kafka.serializer.Serializer):
        def serialize(self, topic, obj):
            return json.dumps(obj).encode("utf-8") if obj is not None else None

    return JSONSerializer()


@pytest.fixture(scope="session")
def json_deserializer():
    class JSONDeserializer(kafka.serializer.Deserializer):
        def deserialize(self, topic, bytes_):
            return json.loads(bytes_.decode("utf-8")) if bytes_ is not None else None

    return JSONDeserializer()


@pytest.fixture(scope="session")
def json_callable_serializer():
    class JSONCallableSerializer(object):
        def __call__(self, obj):
            return json.dumps(obj).encode("utf-8") if obj is not None else None

    return JSONCallableSerializer()


@pytest.fixture(scope="session")
def json_callable_deserializer():
    class JSONCallableDeserializer(object):
        def __call__(self, obj):
            return json.loads(obj.decode("utf-8")) if obj is not None else None

    return JSONCallableDeserializer()


@pytest.fixture(scope="function")
def topic():
    from kafka.admin.client import KafkaAdminClient
    from kafka.admin.new_topic import NewTopic

    topic = "test-topic-%s" % str(uuid.uuid4())

    admin = KafkaAdminClient(bootstrap_servers=BROKER)
    new_topics = [NewTopic(topic, num_partitions=1, replication_factor=1)]
    admin.create_topics(new_topics)

    yield topic

    admin.delete_topics([topic])


@pytest.fixture(scope="session")
def group_id():
    return str(uuid.uuid4())


@pytest.fixture()
def send_producer_message(topic, producer, serialize):
    def _test():
        producer.send(topic, key=serialize("bar"), value=serialize({"foo": 1}))
        producer.flush()

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
            for record in consumer:
                assert deserialize(record.value) == {"foo": 1}
                record_count += 1
            attempts += 1

        assert record_count == 1, "Incorrect count of records consumed: %d. Expected 1." % record_count

    return _test


@transient_function_wrapper(kafka.producer.kafka, "KafkaProducer.send.__wrapped__")
# Place transient wrapper underneath instrumentation
def cache_kafka_producer_headers(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    ret = wrapped(*args, **kwargs)
    headers = kwargs.get("headers", [])
    headers = dict(headers)
    transaction._test_request_headers = headers
    return ret


@transient_function_wrapper(kafka.consumer.group, "KafkaConsumer.__next__")
# Place transient wrapper underneath instrumentation
def cache_kafka_consumer_headers(wrapped, instance, args, kwargs):
    record = wrapped(*args, **kwargs)
    transaction = current_transaction()

    if transaction is None:
        return record

    headers = record.headers
    headers = dict(headers)
    transaction._test_request_headers = headers
    return record


@pytest.fixture(autouse=True)
def assert_no_active_transaction():
    # Run before test
    assert not current_transaction(active_only=False), "Transaction exists before test run."

    yield  # Run test

    # Run after test
    assert not current_transaction(active_only=False), "Transaction was not properly exited."
