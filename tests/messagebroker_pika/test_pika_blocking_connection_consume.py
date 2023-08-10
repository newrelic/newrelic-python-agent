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

import functools
import os

import pika
import pytest
import six
from compat import basic_consume
from conftest import BODY, CORRELATION_ID, EXCHANGE, HEADERS, QUEUE, REPLY_TO
from testing_support.db_settings import rabbitmq_settings
from testing_support.fixtures import capture_transaction_metrics
from testing_support.validators.validate_code_level_metrics import (
    validate_code_level_metrics,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)
from testing_support.validators.validate_tt_collector_json import (
    validate_tt_collector_json,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import end_of_transaction

DB_SETTINGS = rabbitmq_settings()[0]

_message_broker_tt_params = {
    "queue_name": QUEUE,
    "routing_key": QUEUE,
    "correlation_id": CORRELATION_ID,
    "reply_to": REPLY_TO,
    "headers": HEADERS.copy(),
}

_test_blocking_connection_basic_get_metrics = [
    ("MessageBroker/RabbitMQ/Exchange/Produce/Named/%s" % EXCHANGE, None),
    ("MessageBroker/RabbitMQ/Exchange/Consume/Named/%s" % EXCHANGE, 1),
    (("Function/pika.adapters.blocking_connection:" "_CallbackResult.set_value_once"), 1),
]


@validate_transaction_metrics(
    ("test_pika_blocking_connection_consume:" "test_blocking_connection_basic_get"),
    scoped_metrics=_test_blocking_connection_basic_get_metrics,
    rollup_metrics=_test_blocking_connection_basic_get_metrics,
    background_task=True,
)
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
@background_task()
def test_blocking_connection_basic_get(producer):
    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()
        method_frame, _, _ = channel.basic_get(QUEUE)
        assert method_frame
        channel.basic_ack(method_frame.delivery_tag)


_test_blocking_connection_basic_get_empty_metrics = [
    ("MessageBroker/RabbitMQ/Exchange/Produce/Named/%s" % EXCHANGE, None),
    ("MessageBroker/RabbitMQ/Exchange/Consume/Named/%s" % EXCHANGE, None),
]


@validate_transaction_metrics(
    ("test_pika_blocking_connection_consume:" "test_blocking_connection_basic_get_empty"),
    scoped_metrics=_test_blocking_connection_basic_get_empty_metrics,
    rollup_metrics=_test_blocking_connection_basic_get_empty_metrics,
    background_task=True,
)
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
@background_task()
def test_blocking_connection_basic_get_empty():
    QUEUE = "test_blocking_empty-%s" % os.getpid()
    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE)

        try:
            method_frame, _, _ = channel.basic_get(QUEUE)
            assert method_frame is None
        finally:
            channel.queue_delete(queue=QUEUE)


def test_blocking_connection_basic_get_outside_transaction(producer):
    metrics_list = []

    @capture_transaction_metrics(metrics_list)
    def test_basic_get():
        with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE)

            method_frame, _, _ = channel.basic_get(QUEUE)
            channel.basic_ack(method_frame.delivery_tag)
            assert method_frame

    test_basic_get()

    # Confirm that no metrics have been created. This is because no background
    # task should be created for basic_get actions.
    assert not metrics_list


_test_blocking_conn_basic_consume_no_txn_metrics = [
    ("MessageBroker/RabbitMQ/Exchange/Produce/Named/%s" % EXCHANGE, None),
    ("MessageBroker/RabbitMQ/Exchange/Consume/Named/%s" % EXCHANGE, None),
]

if six.PY3:
    _txn_name = (
        "test_pika_blocking_connection_consume:"
        "test_blocking_connection_basic_consume_outside_transaction."
        "<locals>.on_message"
    )
    _test_blocking_conn_basic_consume_no_txn_metrics.append(
        (
            (
                "Function/test_pika_blocking_connection_consume:"
                "test_blocking_connection_basic_consume_outside_transaction."
                "<locals>.on_message"
            ),
            None,
        )
    )
else:
    _txn_name = "test_pika_blocking_connection_consume:" "on_message"
    _test_blocking_conn_basic_consume_no_txn_metrics.append(
        ("Function/test_pika_blocking_connection_consume:on_message", None)
    )


@pytest.mark.parametrize("as_partial", [True, False])
@validate_code_level_metrics(
    "test_pika_blocking_connection_consume"
    + (".test_blocking_connection_basic_consume_outside_transaction.<locals>" if six.PY3 else ""),
    "on_message",
)
@validate_transaction_metrics(
    _txn_name,
    scoped_metrics=_test_blocking_conn_basic_consume_no_txn_metrics,
    rollup_metrics=_test_blocking_conn_basic_consume_no_txn_metrics,
    background_task=True,
    group="Message/RabbitMQ/Exchange/%s" % EXCHANGE,
)
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
def test_blocking_connection_basic_consume_outside_transaction(producer, as_partial):
    def on_message(channel, method_frame, header_frame, body):
        assert hasattr(method_frame, "_nr_start_time")
        assert body == BODY
        channel.stop_consuming()

    if as_partial:
        on_message = functools.partial(on_message)

    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()

        basic_consume(channel, QUEUE, on_message)
        try:
            channel.start_consuming()
        except:
            channel.stop_consuming()
            raise


_test_blocking_conn_basic_consume_in_txn_metrics = [
    ("MessageBroker/RabbitMQ/Exchange/Produce/Named/%s" % EXCHANGE, None),
    ("MessageBroker/RabbitMQ/Exchange/Consume/Named/%s" % EXCHANGE, None),
]

if six.PY3:
    _test_blocking_conn_basic_consume_in_txn_metrics.append(
        (
            (
                "Function/test_pika_blocking_connection_consume:"
                "test_blocking_connection_basic_consume_inside_txn."
                "<locals>.on_message"
            ),
            1,
        )
    )
else:
    _test_blocking_conn_basic_consume_in_txn_metrics.append(
        ("Function/test_pika_blocking_connection_consume:on_message", 1)
    )


@pytest.mark.parametrize("as_partial", [True, False])
@validate_code_level_metrics(
    "test_pika_blocking_connection_consume"
    + (".test_blocking_connection_basic_consume_inside_txn.<locals>" if six.PY3 else ""),
    "on_message",
)
@validate_transaction_metrics(
    ("test_pika_blocking_connection_consume:" "test_blocking_connection_basic_consume_inside_txn"),
    scoped_metrics=_test_blocking_conn_basic_consume_in_txn_metrics,
    rollup_metrics=_test_blocking_conn_basic_consume_in_txn_metrics,
    background_task=True,
)
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
@background_task()
def test_blocking_connection_basic_consume_inside_txn(producer, as_partial):
    def on_message(channel, method_frame, header_frame, body):
        assert hasattr(method_frame, "_nr_start_time")
        assert body == BODY
        channel.stop_consuming()

    if as_partial:
        on_message = functools.partial(on_message)

    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()
        basic_consume(channel, QUEUE, on_message)
        try:
            channel.start_consuming()
        except:
            channel.stop_consuming()
            raise


_test_blocking_conn_basic_consume_stopped_txn_metrics = [
    ("MessageBroker/RabbitMQ/Exchange/Produce/Named/%s" % EXCHANGE, None),
    ("MessageBroker/RabbitMQ/Exchange/Consume/Named/%s" % EXCHANGE, None),
    ("OtherTransaction/Message/RabbitMQ/Exchange/Named/%s" % EXCHANGE, None),
]

if six.PY3:
    _test_blocking_conn_basic_consume_stopped_txn_metrics.append(
        (
            (
                "Function/test_pika_blocking_connection_consume:"
                "test_blocking_connection_basic_consume_stopped_txn."
                "<locals>.on_message"
            ),
            None,
        )
    )
else:
    _test_blocking_conn_basic_consume_stopped_txn_metrics.append(
        ("Function/test_pika_blocking_connection_consume:on_message", None)
    )


@pytest.mark.parametrize("as_partial", [True, False])
@validate_transaction_metrics(
    ("test_pika_blocking_connection_consume:" "test_blocking_connection_basic_consume_stopped_txn"),
    scoped_metrics=_test_blocking_conn_basic_consume_stopped_txn_metrics,
    rollup_metrics=_test_blocking_conn_basic_consume_stopped_txn_metrics,
    background_task=True,
)
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
@background_task()
def test_blocking_connection_basic_consume_stopped_txn(producer, as_partial):
    def on_message(channel, method_frame, header_frame, body):
        assert hasattr(method_frame, "_nr_start_time")
        assert body == BODY
        channel.stop_consuming()

    end_of_transaction()

    if as_partial:
        on_message = functools.partial(on_message)

    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()
        basic_consume(channel, QUEUE, on_message)
        try:
            channel.start_consuming()
        except:
            channel.stop_consuming()
            raise
