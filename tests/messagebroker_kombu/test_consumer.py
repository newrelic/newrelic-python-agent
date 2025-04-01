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
from testing_support.fixtures import override_application_settings, reset_core_stats_engine, validate_attributes
from testing_support.validators.validate_error_event_attributes_outside_transaction import (
    validate_error_event_attributes_outside_transaction,
)
from testing_support.validators.validate_transaction_count import validate_transaction_count
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.transaction import end_of_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.package_version_utils import get_package_version


def test_custom_metrics(get_consumer_record, events, exchange):
    @validate_transaction_metrics(
        f"Named/{exchange.name}",
        group="Message/Kombu/Exchange",
        custom_metrics=[
            (f"Message/Kombu/Exchange/Named/{exchange.name}/Received/Bytes", 1),
            (f"Message/Kombu/Exchange/Named/{exchange.name}/Received/Messages", 1),
            (f"MessageBroker/Kombu/Exchange/Named/{exchange.name}/Serialization/Value", 1),
        ],
        background_task=True,
    )
    def _test():
        get_consumer_record()

        assert len(events) == 1
        assert events[0]["routing_key"]
        assert events[0]["body"] == {"foo": 1}

    _test()


@override_application_settings({"instrumentation.kombu.consumer.enabled": False})
@validate_transaction_count(0)
def test_no_transaction_created_when_kombu_consumer_disabled(get_consumer_record):
    get_consumer_record()


@validate_transaction_count(2)
def test_multiple_transactions(get_consumer_record):
    get_consumer_record()
    get_consumer_record()


def test_custom_metrics_on_existing_transaction(get_consumer_record, exchange):
    version = get_package_version("kombu")

    @validate_transaction_metrics(
        "test_consumer:test_custom_metrics_on_existing_transaction.<locals>._test",
        custom_metrics=[
            (f"Message/Kombu/Exchange/Named/{exchange.name}/Received/Bytes", 1),
            (f"Message/Kombu/Exchange/Named/{exchange.name}/Received/Messages", 1),
            (f"Python/MessageBroker/Kombu/{version}", 1),
            (f"MessageBroker/Kombu/Exchange/Named/{exchange.name}/Serialization/Value", 1),
            ("MessageBroker/Kombu/Exchange/Named/Unknown/Serialization/Value", 1),
        ],
        background_task=True,
    )
    @validate_transaction_count(1)
    @background_task()
    def _test():
        get_consumer_record()

    _test()


def test_custom_metrics_inactive_transaction(get_consumer_record, exchange):
    @validate_transaction_metrics(
        "test_consumer:test_custom_metrics_inactive_transaction.<locals>._test",
        custom_metrics=[
            (f"Message/Kombu/Exchange/Named/{exchange.name}/Received/Bytes", None),
            (f"Message/Kombu/Exchange/Named/{exchange.name}/Received/Messages", None),
        ],
        # + expected_missing_broker_metrics,
        background_task=True,
    )
    @validate_transaction_count(1)
    @background_task()
    def _test():
        end_of_transaction()
        get_consumer_record()

    _test()


def test_agent_attributes(get_consumer_record):
    @validate_attributes("agent", ["kombu.consume.channel_id", "kombu.consume.byteCount"])
    def _test():
        get_consumer_record()

    _test()


def test_consumer_errors(get_consumer_record_error):
    exc_class = RuntimeError

    @reset_core_stats_engine()
    @validate_error_event_attributes_outside_transaction(
        num_errors=1, exact_attrs={"intrinsic": {"error.class": callable_name(exc_class)}, "agent": {}, "user": {}}
    )
    def _test():
        with pytest.raises(exc_class):
            get_consumer_record_error()

    _test()


def test_distributed_tracing_headers(send_producer_message, consumer_connection, consumer_validate_dt, exchange):
    # Produce the messages inside a transaction, making sure to close it.
    @background_task()
    def _produce():
        send_producer_message()

    @validate_transaction_metrics(
        f"Named/{exchange.name}",
        group="Message/Kombu/Exchange",
        rollup_metrics=[
            ("Supportability/DistributedTrace/AcceptPayload/Success", None),
            ("Supportability/TraceContext/Accept/Success", 1),
        ],
        background_task=True,
    )
    @validate_transaction_count(1)
    def _consume():
        def _test():
            consumer_connection.drain_events(timeout=5)

        _test()

    _produce()
    _consume()
