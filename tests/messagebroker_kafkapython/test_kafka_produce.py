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

import time

import kafka
from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics

from conftest import cache_kafka_headers
from testing_support.validators.validate_messagebroker_headers import validate_messagebroker_headers


def test_no_harm(topic, producer, consumer):
    MESSAGES = [
        {"foo": "bar"},
        {"baz": "bat"},
    ]

    for msg in MESSAGES:
        time.sleep(1)
        producer.send(topic, value=msg)
    producer.flush()

    for msg in consumer:
        assert msg.topic == topic


def test_producer(topic, producer, consumer):
    scoped_metrics = [
        ("MessageBroker/Kafka/Topic/Produce/Named/%s" % topic, 3)
    ]
    unscoped_metrics = scoped_metrics


    @validate_transaction_metrics("test_kafka_produce:test_producer.<locals>.test", scoped_metrics=scoped_metrics, rollup_metrics=unscoped_metrics, background_task=True)
    @background_task()
    @cache_kafka_headers
    @validate_messagebroker_headers
    def test():
        messages = [1, 2, 3]
        for message in messages:
            producer.send(topic, message)

        producer.flush()

    test()

