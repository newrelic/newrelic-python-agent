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

import threading
import time

import pytest
from conftest import cache_kafka_producer_headers
from testing_support.validators.validate_messagebroker_headers import validate_messagebroker_headers
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.common.object_names import callable_name


@pytest.mark.parametrize(
    "headers", [[("MY-HEADER", "nonsense")], {"MY-HEADER": "nonsense"}], ids=["list of tuples headers", "dict headers"]
)
@background_task()
def test_produce_arguments(topic, producer, client_type, serialize, headers):
    callback1_called = threading.Event()
    callback2_called = threading.Event()
    ts = int(time.time())

    def producer_callback1(err, msg):
        callback1_called.set()

    def producer_callback2(err, msg):
        callback2_called.set()

    if client_type == "cimpl":
        # Keyword Args
        producer.produce(
            topic=topic,
            value=serialize({"foo": 1}),
            key=serialize("my-key"),
            partition=0,
            callback=producer_callback2,
            timestamp=ts,
            headers=headers,
        )
        # Positional Args
        producer.produce(topic, serialize({"foo": 1}), serialize("my-key"), 0, producer_callback1, None, ts, headers)
    else:
        # Keyword Args
        producer.produce(
            topic=topic,
            value=serialize({"foo": 1}),
            key=serialize("my-key"),
            partition=0,
            on_delivery=producer_callback2,
            timestamp=ts,
            headers=headers,
        )
        # Positional Args
        producer.produce(topic, serialize("my-key"), serialize({"foo": 1}), 0, producer_callback1, ts, headers)
    producer.flush()

    assert callback1_called.wait(5), "Callback never called."
    assert callback2_called.wait(5), "Callback never called."


def test_trace_metrics(topic, send_producer_message, expected_broker_metrics):
    from confluent_kafka import __version__ as version

    scoped_metrics = [(f"MessageBroker/Kafka/Topic/Produce/Named/{topic}", 1)]
    unscoped_metrics = scoped_metrics

    @validate_transaction_metrics(
        "test_producer:test_trace_metrics.<locals>.test",
        scoped_metrics=scoped_metrics,
        rollup_metrics=unscoped_metrics,
        custom_metrics=[(f"Python/MessageBroker/Confluent-Kafka/{version}", 1)] + expected_broker_metrics,
        background_task=True,
    )
    @background_task()
    def test():
        send_producer_message()

    test()


def test_distributed_tracing_headers(topic, send_producer_message, expected_broker_metrics):
    @validate_transaction_metrics(
        "test_producer:test_distributed_tracing_headers.<locals>.test",
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 1),
            ("Supportability/DistributedTrace/CreatePayload/Success", 1),
        ]
        + expected_broker_metrics,
        background_task=True,
    )
    @background_task()
    @cache_kafka_producer_headers()
    @validate_messagebroker_headers
    def test():
        send_producer_message()

    test()


def test_distributed_tracing_headers_under_terminal(topic, send_producer_message, expected_broker_metrics):
    @validate_transaction_metrics(
        "test_distributed_tracing_headers_under_terminal",
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 1),
            ("Supportability/DistributedTrace/CreatePayload/Success", 1),
        ]
        + expected_broker_metrics,
        background_task=True,
    )
    @background_task(name="test_distributed_tracing_headers_under_terminal")
    @cache_kafka_producer_headers()
    @validate_messagebroker_headers
    def test():
        with FunctionTrace(name="terminal_trace", terminal=True):
            send_producer_message()

    test()


def test_producer_errors(topic, producer, monkeypatch):
    if hasattr(producer, "_value_serializer"):
        # Remove serializer to intentionally cause a type error in underlying producer implementation
        monkeypatch.setattr(producer, "_value_serializer", None)

    @validate_transaction_errors([callable_name(TypeError)])
    @background_task()
    def test():
        with pytest.raises(TypeError):
            producer.produce(topic, value=object())
            producer.flush()

    test()


@pytest.fixture(scope="function")
def expected_broker_metrics(broker, topic):
    return [(f"MessageBroker/Kafka/Nodes/{server}/Produce/{topic}", 1) for server in broker.split(",")]
