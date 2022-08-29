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
from conftest import cache_kafka_headers
from testing_support.fixtures import (
    validate_non_transaction_error_event,
    validate_transaction_metrics,
)
from testing_support.validators.validate_messagebroker_headers import (
    validate_messagebroker_headers,
)

from newrelic.api.background_task import background_task


def test_producer_records_trace(topic, send_producer_messages):
    scoped_metrics = [("MessageBroker/Kafka/Topic/Produce/Named/%s" % topic, 3)]
    unscoped_metrics = scoped_metrics

    @validate_transaction_metrics(
        "test_kafka_produce:test_producer_records_trace.<locals>.test",
        scoped_metrics=scoped_metrics,
        rollup_metrics=unscoped_metrics,
        background_task=True,
    )
    @background_task()
    @cache_kafka_headers
    @validate_messagebroker_headers
    def test():
        send_producer_messages()

    test()


def test_producer_records_error_if_raised(topic, producer):
    _intrinsic_attributes = {
        "error.class": "AssertionError",
        "error.message": "Need at least one: key or value",
        "error.expected": False,
    }

    @validate_non_transaction_error_event(_intrinsic_attributes)
    @background_task()
    def test():
        producer.send(topic, None)
        producer.flush()

    with pytest.raises(AssertionError):
        test()


@pytest.fixture
def send_producer_messages(topic, producer):
    def _test():
        messages = [1, 2, 3]
        for message in messages:
            producer.send(topic, message)

        producer.flush()

    return _test
