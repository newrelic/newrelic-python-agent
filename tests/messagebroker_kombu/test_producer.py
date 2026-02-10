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
from conftest import cache_kombu_producer_headers
from kombu.exceptions import EncodeError
from testing_support.validators.validate_messagebroker_headers import validate_messagebroker_headers
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import transient_function_wrapper


def test_trace_metrics(send_producer_message, exchange):
    import kombu

    version = kombu.__version__

    scoped_metrics = [(f"MessageBroker/Kombu/Exchange/Produce/Named/{exchange.name}", 1)]
    unscoped_metrics = scoped_metrics

    @validate_transaction_metrics(
        "test_producer:test_trace_metrics.<locals>.test",
        scoped_metrics=scoped_metrics,
        rollup_metrics=unscoped_metrics,
        custom_metrics=[
            (f"Python/MessageBroker/Kombu/{version}", 1),
            (f"MessageBroker/Kombu/Exchange/Named/{exchange.name}/Serialization/Value", 1),
        ],
        background_task=True,
    )
    @background_task()
    def test():
        send_producer_message()

    test()


def test_distributed_tracing_headers(exchange, send_producer_message):
    @validate_transaction_metrics(
        "test_producer:test_distributed_tracing_headers.<locals>.test",
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 1),
            ("Supportability/DistributedTrace/CreatePayload/Success", 1),
        ],
        background_task=True,
    )
    @background_task()
    @cache_kombu_producer_headers
    @validate_messagebroker_headers
    def test():
        send_producer_message()

    test()


def test_distributed_tracing_headers_under_terminal(exchange, send_producer_message):
    @validate_transaction_metrics(
        "test_distributed_tracing_headers_under_terminal",
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 1),
            ("Supportability/DistributedTrace/CreatePayload/Success", 1),
        ],
        background_task=True,
    )
    @background_task(name="test_distributed_tracing_headers_under_terminal")
    @cache_kombu_producer_headers
    @validate_messagebroker_headers
    def test():
        with FunctionTrace(name="terminal_trace", terminal=True):
            send_producer_message()

    test()


def test_producer_errors(exchange, producer, queue, monkeypatch):
    @validate_transaction_errors([callable_name(EncodeError)])
    @background_task()
    def test():
        with pytest.raises(EncodeError):
            producer.publish({"foo": object()}, exchange=exchange, routing_key="bar", declare=[queue])

    test()


def test_producer_tries_to_parse_args(exchange, producer, queue, monkeypatch):
    @background_task()
    def test():
        with pytest.raises(TypeError):
            producer.publish(
                {"foo": object()}, body={"foo": object()}, exchange=exchange, routing_key="bar", declare=[queue]
            )

    test()


def test_custom_properties(exchange, queue, events, get_consumer_record, producer):
    validate_custom_properties_called = []

    @transient_function_wrapper("kombu.messaging", "Producer._publish")
    def validate_custom_properties(wrapped, instance, args, kwargs):
        from newrelic.common.signature import bind_args

        bound_args = bind_args(wrapped, args, kwargs)
        properties = bound_args["properties"]
        assert properties.get("custom_property", "") == "baz", "custom_property was deleted by instrumentation."
        validate_custom_properties_called.append(True)

    @background_task()
    @validate_custom_properties
    def test():
        producer.publish({"foo": 123}, exchange=exchange, routing_key="bar", declare=[queue], custom_property="baz")

    test()
    assert validate_custom_properties_called, "validate_custom_properties was not called."
