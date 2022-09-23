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
    validate_error_event_attributes_outside_transaction,
    reset_core_stats_engine,
)

from testing_support.validators.validate_transaction_count import validate_transaction_count

from newrelic.api.background_task import background_task
from newrelic.packages import six

from newrelic.common.object_names import callable_name

import json

def test_serialization_metrics(skip_if_not_serializing, topic, send_producer_messages):
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


def test_deserialization_metrics(skip_if_not_serializing, topic, get_consumer_records):
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
        get_consumer_records()

    test()


@pytest.mark.parametrize("key,value", (
    (object(), "A"),
    ("A", object()),
))
def test_serialization_errors(skip_if_not_serializing, topic, producer, key, value):
    error_cls = TypeError

    @validate_transaction_errors([callable_name(error_cls)])
    @background_task()
    def test():
        with pytest.raises(error_cls):
            producer.send(topic=topic, key=key, value=value)

    test()


@pytest.mark.parametrize("key,value", (
    (b"%", b"{}"),
    (b"{}", b"%"),
))
def test_deserialization_errors(skip_if_not_serializing, monkeypatch, topic, producer, consumer, key, value):
    error_cls = json.decoder.JSONDecodeError
    
    # Remove serializers to cause intentional issues
    monkeypatch.setitem(producer.config, "value_serializer", None)
    monkeypatch.setitem(producer.config, "key_serializer", None)

    producer.send(topic=topic, key=key, value=value)
    producer.flush()

    @reset_core_stats_engine()
    @validate_error_event_attributes_outside_transaction(
        num_errors=1,
        exact_attrs={"intrinsic": {"error.class": callable_name(error_cls)}, "agent": {}, "user": {}}
    )
    def test():
        with pytest.raises(error_cls):
            for record in consumer:
                pass
            assert record is not None, "No record consumed."

    test()
