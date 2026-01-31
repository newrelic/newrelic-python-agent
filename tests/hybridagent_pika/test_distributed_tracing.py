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

import os

import pika
from compat import basic_consume
from testing_support.db_settings import rabbitmq_settings
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.encoding_utils import DistributedTracePayload

DB_SETTINGS = rabbitmq_settings()[0]

_override_settings = {
    "primary_application_id": "12345",
    "account_id": "33",
    "trusted_account_key": "1",
    "cross_application_tracer.enabled": True,
    "distributed_tracing.enabled": True,
}


def do_basic_publish(channel, queue_name, properties=None):
    _test_distributed_tracing_basic_publish_metrics = [
        ("Supportability/TraceContext/Create/Success", 2),
        ("Supportability/DistributedTrace/CreatePayload/Success", 2),
        (f"MessageBroker/rabbitmq/Exchange/Produce/Named/{queue_name}", 2),
        ("DurationByCaller/Unknown/Unknown/Unknown/Unknown/all", 1),
        ("DurationByCaller/Unknown/Unknown/Unknown/Unknown/allOther", 1),
    ]

    @validate_transaction_metrics(
        "test_distributed_tracing:do_basic_publish.<locals>._test",
        rollup_metrics=_test_distributed_tracing_basic_publish_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        channel.basic_publish(
            exchange="", routing_key=queue_name, body="Testing distributed_tracing 123", properties=properties
        )

    _test()


def do_basic_consume(channel, queue_name):
    # OTel does not instrument the same functions that New Relic does,
    # so in this case, the produce span is in the context of a BG task,
    # and not a MessageTransaction (from the channel.basic_consume call)
    # BG task to AMQP will make parent app an unknown transport_type.
    _test_distributed_tracing_basic_consume_rollup_metrics = [
        (f"MessageBroker/rabbitmq/Exchange/Produce/Named/{queue_name}", None),
        (f"MessageBroker/rabbitmq/Exchange/Consume/Named/{queue_name}", None),
        ("Supportability/DistributedTrace/AcceptPayload/Success", None),
        ("Supportability/TraceContext/TraceParent/Accept/Success", 1),
        ("Supportability/TraceContext/Accept/Success", 1),
        ("DurationByCaller/App/33/12345/Unknown/all", 1),
        ("TransportDuration/App/33/12345/Unknown/all", 1),
        ("DurationByCaller/App/33/12345/Unknown/allOther", 1),
        ("TransportDuration/App/33/12345/Unknown/allOther", 1),
    ]

    @validate_transaction_metrics(
        f"{queue_name}",
        rollup_metrics=_test_distributed_tracing_basic_consume_rollup_metrics,
        background_task=True,
        group="Message/rabbitmq/Exchange/Named",
    )
    def _test():
        channel.start_consuming()

    _test()


@override_application_settings(_override_settings)
def test_basic_consume_distributed_tracing_headers():
    def on_receive(ch, method, properties, msg):
        headers = properties.headers
        assert headers
        assert "NewRelicID" not in headers
        assert "NewRelicTransaction" not in headers
        assert msg == b"Testing distributed_tracing 123"
        txn = current_transaction()

        assert txn
        assert txn._distributed_trace_state
        assert txn.parent_type == "App"
        assert txn._trace_id.startswith(txn.parent_tx)
        assert txn.parent_span is not None
        assert txn.parent_account == txn.settings.account_id
        assert txn._priority is not None
        assert txn._sampled is not None

        ch.stop_consuming()

    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()
        queue_name = f"TESTDT-{os.getpid()}"
        channel.queue_declare(queue_name, durable=False)

        properties = pika.BasicProperties()
        properties.headers = {"Hello": "World"}

        try:
            basic_consume(channel, queue_name, on_receive, auto_ack=False)
            do_basic_publish(channel, queue_name, properties=properties)
            do_basic_consume(channel, queue_name)

        finally:
            channel.queue_delete(queue_name)


_test_distributed_tracing_basic_get_metrics = [
    ("MessageBroker/rabbitmq/Exchange/Produce/Named/Default", None),
    ("MessageBroker/rabbitmq/Exchange/Consume/Named/Default", None),
    ("DurationByCaller/Unknown/Unknown/Unknown/Unknown/all", 1),
    ("DurationByCaller/Unknown/Unknown/Unknown/Unknown/allOther", 1),
]


# NOTE: channel.basic_get is not instrumented by OTel pika instrumentation,
# so we use a background task here to simulate the transaction context.
@validate_transaction_metrics(
    "test_distributed_tracing:do_basic_get",
    rollup_metrics=_test_distributed_tracing_basic_get_metrics,
    background_task=True,
)
@background_task()
def do_basic_get(channel, QUEUE):
    _, properties, msg = channel.basic_get(QUEUE)
    headers = properties.headers

    assert headers
    assert msg == b"Testing distributed_tracing 123"

    assert "traceparent" in headers
    assert "tracestate" in headers


@override_application_settings(_override_settings)
def test_basic_get_no_distributed_tracing_headers():
    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()
        queue_name = f"TESTDT-{os.getpid()}"
        channel.queue_declare(queue_name, durable=False)

        properties = pika.BasicProperties()
        properties.headers = {"Hello": "World"}

        try:
            do_basic_publish(channel, queue_name, properties=properties)
            do_basic_get(channel, queue_name)
        finally:
            channel.queue_delete(queue_name)


@override_application_settings(_override_settings)
def test_distributed_tracing_sends_produce_id():
    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()
        queue_name = f"TESTDT-{os.getpid()}"
        channel.queue_declare(queue_name, durable=False)

        properties = pika.BasicProperties()
        properties.headers = {"Hello": "World"}

        try:

            @background_task()
            def _publish():
                with FunctionTrace("foo") as trace:
                    channel.basic_publish(
                        exchange="",
                        routing_key=queue_name,
                        body="Testing distributed_tracing 123",
                        properties=properties,
                    )

                return trace

            trace = _publish()

            raw_message = channel.basic_get(queue_name)
        finally:
            channel.queue_delete(queue_name)

        properties = raw_message[1]
        payload = DistributedTracePayload.from_http_safe(properties.headers["newrelic"])

        data = payload["d"]

        # The payload should NOT contain the function trace ID
        assert data["id"] != trace.guid
