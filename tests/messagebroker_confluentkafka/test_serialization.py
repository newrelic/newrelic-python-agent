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

import pytest
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name
from newrelic.packages import six


def test_serialization_metrics(skip_if_not_serializing, topic, send_producer_message):
    txn_name = "test_serialization:test_serialization_metrics.<locals>.test" if six.PY3 else "test_serialization:test"

    _metrics = [
        ("MessageBroker/Kafka/Topic/Named/%s/Serialization/Value" % topic, 1),
        ("MessageBroker/Kafka/Topic/Named/%s/Serialization/Key" % topic, 1),
    ]

    @validate_transaction_metrics(
        txn_name,
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    @background_task()
    def test():
        send_producer_message()

    test()


def test_deserialization_metrics(skip_if_not_serializing, topic, get_consumer_record):
    _metrics = [
        ("Message/Kafka/Topic/Named/%s/Deserialization/Value" % topic, 1),
        ("Message/Kafka/Topic/Named/%s/Deserialization/Key" % topic, 1),
    ]

    @validate_transaction_metrics(
        "Named/%s" % topic,
        group="Message/Kafka/Topic",
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    def test():
        get_consumer_record()

    test()


@pytest.mark.parametrize(
    "key,value,error",
    (
        (object(), "A", "KeySerializationError"),
        ("A", object(), "ValueSerializationError"),
    ),
)
def test_serialization_errors(skip_if_not_serializing, topic, producer, key, value, error):
    import confluent_kafka.error

    error_cls = getattr(confluent_kafka.error, error)

    @validate_transaction_errors([callable_name(error_cls)])
    @background_task()
    def test():
        with pytest.raises(error_cls):
            producer.produce(topic=topic, key=key, value=value)

    test()


@pytest.mark.parametrize(
    "key,value,error",
    (
        ("%", "{}", "KeyDeserializationError"),
        ("{}", "%", "ValueDeserializationError"),
    ),
)
def test_deserialization_errors(skip_if_not_serializing, monkeypatch, topic, producer, consumer, key, value, error):
    import confluent_kafka.error

    error_cls = getattr(confluent_kafka.error, error)

    # Remove serializers to cause intentional issues
    monkeypatch.setattr(producer, "_value_serializer", None)
    monkeypatch.setattr(producer, "_key_serializer", None)

    producer.produce(topic=topic, key=key, value=value)
    producer.flush()

    @validate_transaction_errors([callable_name(error_cls)])
    @background_task()
    def test():
        with pytest.raises(error_cls):
            timeout = 10
            attempts = 0
            while attempts < timeout:
                if not consumer.poll(0.5):
                    attempts += 1
                    continue

    test()


@pytest.fixture
def send_producer_message(topic, producer):
    def _test():
        producer.produce(topic, value={"foo": 1})
        producer.flush()

    return _test


@pytest.fixture()
def get_consumer_record(topic, send_producer_message, consumer):
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

            assert record.value() == {"foo": 1}
            record_count += 1
        consumer.poll(0.5)  # Exit the transaction.

        assert record_count == 1, "Incorrect count of records consumed: %d. Expected 1." % record_count

    return _test
