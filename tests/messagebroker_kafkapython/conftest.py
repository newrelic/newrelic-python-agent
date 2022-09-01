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

import json
import uuid

import kafka
import pytest
from testing_support.db_settings import kafka_settings
from testing_support.fixtures import (  # noqa: F401
    code_coverage_fixture,
    collector_agent_registration_fixture,
    collector_available_fixture,
)

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import transient_function_wrapper

DB_SETTINGS = kafka_settings()[0]

BOOTSTRAP_SERVER = "%s:%s" % (DB_SETTINGS["host"], DB_SETTINGS["port"])
BROKER = [BOOTSTRAP_SERVER]

_coverage_source = [
    "newrelic.hooks.messagebroker_kafkapython",
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (messagebroker_kafkapython)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (messagebroker_kafkapython)"],
)


@pytest.fixture(scope="function")
def producer():
    producer = kafka.KafkaProducer(
        bootstrap_servers=BROKER, api_version=(2, 0, 2), value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    yield producer
    producer.close()


@pytest.fixture(scope="function")
def consumer(topic):
    consumer = kafka.KafkaConsumer(
        topic,
        bootstrap_servers=BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
        heartbeat_interval_ms=1000,
        group_id="test",
    )
    yield consumer
    consumer.close()


@pytest.fixture(scope="function")
def topic():
    yield "test-topic-%s" % str(uuid.uuid4())


@transient_function_wrapper(kafka.producer.kafka, "KafkaProducer.send.__wrapped__")
# Place transient wrapper underneath instrumentation
def cache_kafka_headers(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    ret = wrapped(*args, **kwargs)
    headers = kwargs.get("headers", [])
    headers = dict(headers)
    transaction._test_request_headers = headers
    return ret
