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
from conftest import cache_kafka_consumer_headers
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.validators.validate_distributed_trace_accepted import (
    validate_distributed_trace_accepted,
)
from testing_support.validators.validate_error_event_attributes_outside_transaction import (
    validate_error_event_attributes_outside_transaction,
)
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import end_of_transaction
from newrelic.common.object_names import callable_name
from newrelic.packages import six


def test_custom_metrics(get_consumer_record, topic):
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
        get_consumer_record()

    _test()


def test_multiple_transactions(get_consumer_record, topic):
    @validate_transaction_count(2)
    def _test():
        get_consumer_record()
        get_consumer_record()

    _test()


def test_custom_metrics_on_existing_transaction(get_consumer_record, topic):
    from kafka.version import __version__ as version

    transaction_name = (
        "test_consumer:test_custom_metrics_on_existing_transaction.<locals>._test" if six.PY3 else "test_consumer:_test"
    )

    @validate_transaction_metrics(
        transaction_name,
        custom_metrics=[
            ("Message/Kafka/Topic/Named/%s/Received/Bytes" % topic, 1),
            ("Message/Kafka/Topic/Named/%s/Received/Messages" % topic, 1),
            ("Python/MessageBroker/Kafka-Python/%s" % version, 1),
        ],
        background_task=True,
    )
    @validate_transaction_count(1)
    @background_task()
    def _test():
        get_consumer_record()

    _test()


def test_custom_metrics_inactive_transaction(get_consumer_record, topic):
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
        get_consumer_record()

    _test()


def test_agent_attributes(get_consumer_record):
    @validate_attributes("agent", ["kafka.consume.client_id", "kafka.consume.byteCount"])
    def _test():
        get_consumer_record()

    _test()


def test_consumer_errors(get_consumer_record, consumer_next_raises):
    exc_class = RuntimeError

    @reset_core_stats_engine()
    @validate_error_event_attributes_outside_transaction(
        num_errors=1, exact_attrs={"intrinsic": {"error.class": callable_name(exc_class)}, "agent": {}, "user": {}}
    )
    def _test():
        with pytest.raises(exc_class):
            get_consumer_record()

    _test()


def test_consumer_handled_errors_not_recorded(get_consumer_record):
    # It's important to check that we do not notice the StopIteration error.
    @validate_transaction_errors([])
    def _test():
        get_consumer_record()

    _test()


def test_distributed_tracing_headers(topic, producer, consumer, serialize):
    # Produce the messages inside a transaction, making sure to close it.
    @background_task()
    def _produce():
        producer.send(topic, key=serialize("bar"), value=serialize({"foo": 1}))
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
        consumer_iter = iter(consumer)

        @validate_distributed_trace_accepted(transport_type="Kafka")
        @cache_kafka_consumer_headers
        def _test():
            # Start the transaction but don't exit it.
            timeout = 10
            attempts = 0
            record = None
            while not record and attempts < timeout:
                try:
                    record = next(consumer_iter)
                except StopIteration:
                    attempts += 1

        _test()

        # Exit the transaction.
        with pytest.raises(StopIteration):
            next(consumer_iter)

    _produce()
    _consume()


@pytest.fixture()
def consumer_next_raises(consumer):
    def _poll(*args, **kwargs):
        raise RuntimeError()

    consumer.poll = _poll
    return consumer
