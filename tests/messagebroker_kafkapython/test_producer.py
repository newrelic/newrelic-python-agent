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
from testing_support.validators.validate_messagebroker_headers import (
    validate_messagebroker_headers,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name
from newrelic.packages import six


def test_trace_metrics(topic, send_producer_message):
    from kafka.version import __version__ as version

    scoped_metrics = [("MessageBroker/Kafka/Topic/Produce/Named/%s" % topic, 1)]
    unscoped_metrics = scoped_metrics
    txn_name = "test_producer:test_trace_metrics.<locals>.test" if six.PY3 else "test_producer:test"

    @validate_transaction_metrics(
        txn_name,
        scoped_metrics=scoped_metrics,
        rollup_metrics=unscoped_metrics,
        custom_metrics=[("Python/MessageBroker/Kafka-Python/%s" % version, 1)],
        background_task=True,
    )
    @background_task()
    def test():
        send_producer_message()

    test()


def test_distributed_tracing_headers(topic, send_producer_message):
    txn_name = "test_producer:test_distributed_tracing_headers.<locals>.test" if six.PY3 else "test_producer:test"

    @validate_transaction_metrics(
        txn_name,
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 1),
            ("Supportability/DistributedTrace/CreatePayload/Success", 1),
        ],
        background_task=True,
    )
    @background_task()
    @cache_kafka_producer_headers
    @validate_messagebroker_headers
    def test():
        send_producer_message()

    test()


def test_producer_errors(topic, producer, monkeypatch):
    monkeypatch.setitem(producer.config, "value_serializer", None)
    monkeypatch.setitem(producer.config, "key_serializer", None)

    @validate_transaction_errors([callable_name(AssertionError)])
    @background_task()
    def test():
        with pytest.raises(AssertionError):
            producer.send(topic, value=object())
            producer.flush()

    test()
