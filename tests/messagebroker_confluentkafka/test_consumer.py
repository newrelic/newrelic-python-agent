# # Copyright 2010 New Relic, Inc.
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #      http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.

import pytest
from conftest import cache_kafka_consumer_headers
from testing_support.fixtures import (
    validate_attributes,
    validate_error_event_attributes_outside_transaction,
    validate_transaction_errors,
    validate_transaction_metrics,
)
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)
from testing_support.validators.validate_distributed_trace_accepted import (
    validate_distributed_trace_accepted,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import end_of_transaction
from newrelic.packages import six


def test_custom_metrics(get_consumer_records, producer, topic):
    from confluent_kafka import SerializingProducer

    custom_metrics = [
        ("Message/Kafka/Topic/Named/%s/Received/Bytes" % topic, 1),
        ("Message/Kafka/Topic/Named/%s/Received/Messages" % topic, 1),
    ]
    if isinstance(producer, SerializingProducer):
        custom_metrics.extend([
            ("Message/Kafka/Topic/Named/%s/Deserialization/Value" % topic, 1),
            ("Message/Kafka/Topic/Named/%s/Deserialization/Key" % topic, 1),
        ])

    @validate_transaction_metrics(
        "Named/%s" % topic,
        group="Message/Kafka/Topic",
        custom_metrics=custom_metrics,
        background_task=True,
    )
    @validate_transaction_count(1)
    def _test():
        get_consumer_records()

    _test()


def test_custom_metrics_on_existing_transaction(get_consumer_records, topic):
    transaction_name = (
        "test_consumer:test_custom_metrics_on_existing_transaction.<locals>._test" if six.PY3 else "test_consumer:_test"
    )

    @validate_transaction_metrics(
        transaction_name,
        custom_metrics=[
            ("Message/Kafka/Topic/Named/%s/Received/Bytes" % topic, 1),
            ("Message/Kafka/Topic/Named/%s/Received/Messages" % topic, 1),
        ],
        background_task=True,
    )
    @validate_transaction_count(1)
    @background_task()
    def _test():
        get_consumer_records()

    _test()


def test_custom_metrics_inactive_transaction(get_consumer_records, topic):
    transaction_name = (
        "test_consumer:test_custom_metrics_inactive_transaction.<locals>._test" if six.PY3 else "test_consumer:_test"
    )

    @validate_transaction_metrics(
        transaction_name,
        custom_metrics=[
            ("Message/Kafka/Topic/Named/%s/Received/Bytes" % topic, None),
            ("Message/Kafka/Topic/Named/%s/Received/Messages" % topic, None),
        ],
        background_task=True,
    )
    @validate_transaction_count(1)
    @background_task()
    def _test():
        end_of_transaction()
        get_consumer_records()

    _test()


def test_agent_attributes(get_consumer_records):
    @validate_attributes("agent", ["kafka.consume.byteCount"])
    def _test():
        get_consumer_records()

    _test()


def test_consumer_errors(topic, consumer, producer, producer_cimpl):
    from confluent_kafka import SerializingProducer
    from confluent_kafka.error import ValueDeserializationError

    if isinstance(producer, SerializingProducer):
        expected_error = ValueDeserializationError
    else:
        # Close the consumer in order to force poll to raise an exception.
        consumer.close()
        expected_error = RuntimeError

    @validate_error_event_attributes_outside_transaction(
        exact_attrs={"intrinsic": {"error.class": expected_error.__name__}}
    )
    def _test():
        with pytest.raises(expected_error):
            producer_cimpl.produce(topic, value=b"%")  # Invalid JSON
            producer_cimpl.flush()
            while consumer.poll(0.5):
                pass

    _test()


def test_consumer_handled_errors_not_recorded(get_consumer_records):
    # It's important to check that we do not notice the StopIteration error.
    @validate_transaction_errors([])
    def _test():
        get_consumer_records()

    _test()


def test_distributed_tracing_headers(topic, producer, consumer, serialize):
    # produce the messages inside a transaction, making sure to close it.
    @validate_transaction_count(1)
    @background_task()
    def _produce():
        producer.produce(topic, value=serialize({"foo": "bar"}))
        producer.flush()

    @validate_transaction_metrics(
        "Named/%s" % topic,
        group="Message/Kafka/Topic",
        rollup_metrics=[
            ("Supportability/DistributedTrace/AcceptPayload/Success", None),
            ("Supportability/TraceContext/Accept/Success", 1),
        ],
        background_task=True,
    )
    @validate_transaction_count(1)
    def _consume():
        @validate_distributed_trace_accepted(transport_type="Kafka")
        @cache_kafka_consumer_headers()
        def _test():
            # Start the transaction but don't exit it.
            consumer.poll(0.5)

        _test()

        # Exit the transaction.
        consumer.poll(0.5)

    _produce()
    _consume()


@pytest.fixture()
def get_consumer_records(topic, producer, consumer, serialize, deserialize):
    def _test():
        producer.produce(topic, key="1", value=serialize({"foo": "bar"}))
        producer.flush()

        record_count = 0
        while True:
            record = consumer.poll(0.5)
            if not record:
                break
            assert not record.error()

            record_count += 1
            assert deserialize(record.value()) == {"foo": "bar"}

        assert record_count, "No records consumed."

    return _test
