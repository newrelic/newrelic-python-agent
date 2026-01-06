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
from testing_support.validators.validate_messagebroker_headers import validate_messagebroker_headers
from testing_support.validators.validate_transaction_count import validate_transaction_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace


def test_trace_metrics(topic, send_producer_message, expected_broker_metrics):
    scoped_metrics = [(f"MessageBroker/Kafka/Topic/Produce/Named/{topic} send", 1)]
    unscoped_metrics = scoped_metrics

    @validate_transaction_metrics(
        "test_producer:test_trace_metrics.<locals>.test",
        scoped_metrics=scoped_metrics,
        rollup_metrics=unscoped_metrics,
        custom_metrics=[*expected_broker_metrics],
        background_task=True,
    )
    @background_task()
    def test():
        send_producer_message()

    test()


def test_trace_not_being_created(send_producer_message):
    @validate_transaction_count(0)
    def test():
        send_producer_message()

    test()


def test_distributed_tracing_headers(topic, send_producer_message, expected_broker_metrics):
    @validate_transaction_metrics(
        "test_producer:test_distributed_tracing_headers.<locals>.test",
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 1),
            ("Supportability/DistributedTrace/CreatePayload/Success", 1),
            *expected_broker_metrics,
        ],
        background_task=True,
    )
    @background_task()
    @cache_kafka_producer_headers
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
            *expected_broker_metrics,
        ],
        background_task=True,
    )
    @background_task(name="test_distributed_tracing_headers_under_terminal")
    @cache_kafka_producer_headers
    @validate_messagebroker_headers
    def test():
        with FunctionTrace(name="terminal_trace", terminal=True):
            send_producer_message()

    test()


@pytest.fixture
def expected_broker_metrics(broker, topic):
    return [(f"MessageBroker/Kafka/Nodes/{server}/Produce/{topic}", 1) for server in broker]
