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
from conftest import cache_kafka_producer_headers
from testing_support.fixtures import (
    validate_transaction_errors,
    validate_transaction_metrics,
)
from testing_support.validators.validate_messagebroker_headers import (
    validate_messagebroker_headers,
)

from newrelic.api.background_task import background_task
from newrelic.packages import six

from newrelic.common.object_names import callable_name


def test_trace_metrics(topic, send_producer_messages):
    scoped_metrics = [("MessageBroker/Kafka/Topic/Produce/Named/%s" % topic, 3)]
    unscoped_metrics = scoped_metrics
    txn_name = "test_producer:test_trace_metrics.<locals>.test" if six.PY3 else "test_producer:test"

    @validate_transaction_metrics(
        txn_name,
        scoped_metrics=scoped_metrics,
        rollup_metrics=unscoped_metrics,
        background_task=True,
    )
    @background_task()
    def test():
        send_producer_messages()

    test()


def test_serialization_metrics(topic, producer_serializing):
    txn_name = "test_producer:test_serialization_metrics.<locals>.test" if six.PY3 else "test_producer:test"

    @validate_transaction_metrics(
        txn_name,
        custom_metrics=[
            ("MessageBroker/Kafka/Topic/Named/%s/Serialization/Value" % topic, 3),
            ("MessageBroker/Kafka/Topic/Named/%s/Serialization/Key" % topic, 3),
        ],
        background_task=True,
    )
    @background_task()
    def test():
        messages = [1, 2, 3]
        for message in messages:
            producer_serializing.produce(topic, key="1", value=message)

        producer_serializing.flush()

    test()


def test_distributed_tracing_headers(topic, send_producer_messages):
    txn_name = "test_producer:test_distributed_tracing_headers.<locals>.test" if six.PY3 else "test_producer:test"

    @validate_transaction_metrics(
        txn_name,
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 3),
            ("Supportability/DistributedTrace/CreatePayload/Success", 3),
        ],
        background_task=True,
    )
    @background_task()
    @cache_kafka_producer_headers()
    @validate_messagebroker_headers
    def test():
        send_producer_messages()

    test()


def test_producer_errors(topic, producer):
    # from confluent_kafka import SerializingProducer
    from confluent_kafka.error import ValueSerializationError

    @validate_transaction_errors([callable_name(TypeError)])
    @background_task()
    def test():
        with pytest.raises((TypeError, ValueSerializationError)):
            producer.produce(topic, value=object())
            producer.flush()

    test()


@pytest.fixture
def send_producer_messages(topic, producer, serialize):
    def _test():
        messages = [1, 2, 3]
        for message in messages:
            producer.produce(topic, value=serialize(message))

        producer.flush()

    return _test
