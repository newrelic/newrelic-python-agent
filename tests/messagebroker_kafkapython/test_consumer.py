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

import kafka
import kafka.errors as Errors
import pytest
from conftest import BROKER, cache_kafka_consumer_headers
from testing_support.fixtures import (
    validate_attributes,
    validate_error_event_attributes_outside_transaction,
    validate_transaction_errors,
    validate_transaction_metrics,
)
from testing_support.validators.validate_messagebroker_headers import (
    validate_messagebroker_headers,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import end_of_transaction
from newrelic.packages import six
from testing_support.validators.validate_distributed_trace_accepted import validate_distributed_trace_accepted


def test_custom_metrics(get_consumer_records, topic):
    @validate_transaction_metrics(
        "Named/%s" % topic,
        group="Message/Kafka/Topic",
        custom_metrics=[
            ("Message/Kafka/Topic/Named/%s/Received/Bytes" % topic, 1),
            ("Message/Kafka/Topic/Named/%s/Received/Messages" % topic, 1),
        ],
        background_task=True,
    )
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
    @background_task()
    def _test():
        end_of_transaction()
        get_consumer_records()

    _test()


def test_agent_attributes(get_consumer_records):
    @validate_attributes("agent", ["kafka.consume.client_id", "kafka.consume.byteCount"])
    def _test():
        get_consumer_records()

    _test()


def test_consumer_errors(get_consumer_records, consumer_next_raises):
    @validate_error_event_attributes_outside_transaction(
        exact_attrs={"intrinsic": {"error.class": "kafka.errors:KafkaError"}}
    )
    def _test():
        with pytest.raises(Errors.KafkaError):
            get_consumer_records()

    _test()


def test_consumer_deserialization_errors(topic, consumer):
    producer = kafka.KafkaProducer(
        bootstrap_servers=BROKER, api_version=(2, 0, 2), value_serializer=lambda v: str(v).encode("utf-8")
    )  # Producer that allows us to upload invalid JSON.

    @validate_error_event_attributes_outside_transaction(exact_attrs={"intrinsic": {"error.class": "ValueError"}})
    def _test():
        with pytest.raises(ValueError):
            producer.send(topic, value="%")  # Invalid JSON
            producer.flush()
            for _ in consumer:
                pass

    _test()


def test_consumer_handled_errors_not_recorded(get_consumer_records):
    # It's important to check that we do not notice the StopIteration error.
    @validate_transaction_errors([])
    def _test():
        get_consumer_records()

    _test()


def test_distributed_tracing_headers(topic, producer, consumer):
    # Send the messages inside a transaction, making sure to close it.
    @background_task()
    def _produce():
        producer.send(topic, value={"foo": "bar"})
        producer.flush()

    consumer_iter = iter(consumer)

    @validate_transaction_metrics(
        "Named/%s" % topic,
        group="Message/Kafka/Topic",
        rollup_metrics=[
            ("Supportability/DistributedTrace/AcceptPayload/Success", None),
            ("Supportability/TraceContext/Accept/Success", 1),
        ],
        background_task=True,
    )
    def _consume():
        @validate_distributed_trace_accepted(transport_type="Kafka")
        @cache_kafka_consumer_headers
        def _test():
            # Start the transaction but don't exit it.
            next(consumer_iter)

        _test()

        # Exit the transaction.
        with pytest.raises(StopIteration):
            next(consumer_iter)

    _produce()
    _consume()


@pytest.fixture()
def get_consumer_records(topic, producer, consumer):
    def _test():
        producer.send(topic, value={"foo": "bar"})
        producer.flush()
        for record in consumer:
            assert record.value == {"foo": "bar"}

    return _test


@pytest.fixture()
def consumer_next_raises(consumer):
    def _poll(*args, **kwargs):
        raise Errors.KafkaError()

    consumer.poll = _poll
    consumer
