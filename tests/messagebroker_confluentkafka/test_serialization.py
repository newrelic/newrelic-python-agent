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
from testing_support.fixtures import (
    validate_transaction_errors,
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.packages import six

from newrelic.common.object_names import callable_name


@pytest.fixture
def send_producer_messages(topic, producer_serializing):
    def _test():
        producer_serializing.produce(topic, value={"foo": 1})
        producer_serializing.flush()

    return _test


@pytest.fixture()
def get_consumer_records(topic, send_producer_messages, producer_serializing, consumer_deserializing):
    def _test():
        send_producer_messages()

        record_count = 0
        while True:
            record = consumer_deserializing.poll(0.5)
            if not record:
                break
            assert not record.error()

            assert record.value() == {"foo": 1}
            record_count += 1

        assert record_count == 1, "Incorrect count of records consumed: %d. Expected 1." % record_count

    return _test


def test_serialization_metrics(topic, send_producer_messages):
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
        send_producer_messages()

    test()


def test_deserialization_metrics(topic, get_consumer_records):
    txn_name = "test_serialization:test_deserialization_metrics.<locals>.test" if six.PY3 else "test_serialization:test"

    _metrics = [
        ("MessageBroker/Kafka/Topic/Named/%s/Deserialization/Value" % topic, 1),
        ("MessageBroker/Kafka/Topic/Named/%s/Deserialization/Key" % topic, 1),
    ]

    @validate_transaction_metrics(
        txn_name,
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    @background_task()
    def test():
        get_consumer_records()

    test()


@pytest.mark.parametrize("key,value,error", (
    (object(), "A", "KeySerializationError"),
    ("A", object(), "ValueSerializationError"),
))
def test_serialization_errors(topic, producer_serializing, key, value, error):
    import confluent_kafka.error
    error = getattr(confluent_kafka.error, error)

    @validate_transaction_errors([callable_name(error)])
    @background_task()
    def test():
        with pytest.raises(error):
            producer_serializing.produce(topic=topic, key=key, value=value)

    test()


@pytest.mark.parametrize("key,value,error", (
    ("%", "A", "KeyDeserializationError"),
    ("A", "%", "ValueDeserializationError"),
))
def test_deserialization_errors(topic, producer_cimpl, consumer_deserializing, key, value, error):
    import confluent_kafka.error
    error = getattr(confluent_kafka.error, error)

    producer_cimpl.produce(topic=topic, key=key, value=value)
    producer_cimpl.flush()

    @validate_transaction_errors([callable_name(error)])
    @background_task()
    def test():
        with pytest.raises(error):
            record = consumer_deserializing.poll(0.5)
            assert record is not None, "No record consumed."

    test()
