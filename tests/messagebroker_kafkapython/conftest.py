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

from datetime import datetime
import kafka
import json
import time
import pytest
import uuid
from threading import Thread

from testing_support.db_settings import kafka_settings
from testing_support.fixtures import (code_coverage_fixture,  # NOQA
        collector_agent_registration_fixture, collector_available_fixture)

DB_SETTINGS = kafka_settings()[0]
BOOTSTRAP_SERVER = ":".join(str(val) for val in DB_SETTINGS.values())
BROKER = [BOOTSTRAP_SERVER]
TOPIC = "test-topic-%d" % datetime.now().timestamp()
MESSAGES = [
        {"foo": "bar"},
        {"baz": "bat"},
        {"user1": "Hello!"},
        {"user2": "Hola!"},
]

_coverage_source = [
    'newrelic.hooks.messagebroker_kafkapython',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (messagebroker_kafkapython)',
        default_settings=_default_settings,
        linked_applications=['Python Agent Test (messagebroker_kafkapython)'])


consumer = kafka.KafkaConsumer(
    TOPIC,
    bootstrap_servers=BROKER,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    auto_offset_reset="earliest",
    consumer_timeout_ms=5000,
)

producer = kafka.KafkaProducer(
    bootstrap_servers=BROKER, api_version=(2, 0, 2), value_serializer=lambda v: json.dumps(v).encode("utf-8")
)


def produce():
    for msg in MESSAGES:
        time.sleep(1)
        producer.send(TOPIC, value=msg)
    producer.flush()


def consume():
    for msg in consumer:
        assert msg.topic == TOPIC


def execute_threads():
    t1 = Thread(target=produce)
    t2 = Thread(target=consume)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
