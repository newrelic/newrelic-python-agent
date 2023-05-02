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
import random
import string

import pika
import six
from compat import basic_consume
from testing_support.db_settings import rabbitmq_settings
from testing_support.fixtures import (
    cat_enabled,
    override_application_settings,
)
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

DB_SETTINGS = rabbitmq_settings()[0]

ENCODING_KEY = "".join(random.choice(string.ascii_lowercase) for _ in range(40))
_override_settings = {
    "cross_process_id": "1#1",
    "encoding_key": ENCODING_KEY,
    "trusted_account_ids": [1],
    "browser_monitoring.enabled": False,
}


@background_task()
def do_basic_publish(channel, QUEUE, properties=None):
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE,
        body="Testing CAT 123",
        properties=properties,
    )


_test_cat_basic_consume_scoped_metrics = [
    ("MessageBroker/RabbitMQ/Exchange/Produce/Named/Default", None),
    ("MessageBroker/RabbitMQ/Exchange/Consume/Named/Default", None),
]
_test_cat_basic_consume_rollup_metrics = list(_test_cat_basic_consume_scoped_metrics)
_test_cat_basic_consume_rollup_metrics.append(("ClientApplication/1#1/all", 1))
if six.PY3:
    _txn_name = "test_cat:test_basic_consume_cat_headers.<locals>.on_receive"
else:
    _txn_name = "test_cat:on_receive"


@validate_transaction_metrics(
    _txn_name,
    scoped_metrics=_test_cat_basic_consume_scoped_metrics,
    rollup_metrics=_test_cat_basic_consume_rollup_metrics,
    background_task=True,
    group="Message/RabbitMQ/Exchange/Default",
)
def do_basic_consume(channel):
    channel.start_consuming()


@cat_enabled
@override_application_settings(_override_settings)
def test_basic_consume_cat_headers():
    def on_receive(ch, method, properties, msg):
        headers = properties.headers
        assert headers
        assert "NewRelicID" not in headers
        assert "NewRelicTransaction" not in headers
        assert msg == b"Testing CAT 123"
        txn = current_transaction()
        assert txn.client_cross_process_id == "1#1"
        assert txn.client_account_id == 1
        assert txn.client_application_id == 1
        ch.stop_consuming()

    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()
        queue_name = "TESTCAT-%s" % os.getpid()
        channel.queue_declare(queue_name, durable=False)

        properties = pika.BasicProperties()
        properties.headers = {"Hello": "World"}

        try:
            basic_consume(channel, queue_name, on_receive, auto_ack=False)
            do_basic_publish(channel, queue_name, properties=properties)
            do_basic_consume(channel)

        finally:
            channel.queue_delete(queue_name)


_test_cat_basic_get_metrics = [
    ("MessageBroker/RabbitMQ/Exchange/Produce/Named/Default", None),
    ("MessageBroker/RabbitMQ/Exchange/Consume/Named/Default", 1),
    # Verify basic_get doesn't create a CAT metric
    ("ClientApplication/1#1/all", None),
]


@validate_transaction_metrics(
    "test_cat:do_basic_get",
    scoped_metrics=_test_cat_basic_get_metrics,
    rollup_metrics=_test_cat_basic_get_metrics,
    background_task=True,
)
@background_task()
def do_basic_get(channel, QUEUE):
    _, properties, msg = channel.basic_get(QUEUE)
    headers = properties.headers
    assert headers
    assert "NewRelicID" not in headers
    assert "NewRelicTransaction" not in headers
    assert msg == b"Testing CAT 123"
    txn = current_transaction()
    assert txn.client_cross_process_id is None
    assert txn.client_account_id is None
    assert txn.client_application_id is None


@override_application_settings(_override_settings)
def test_basic_get_no_cat_headers():
    with pika.BlockingConnection(pika.ConnectionParameters(DB_SETTINGS["host"])) as connection:
        channel = connection.channel()
        queue_name = "TESTCAT-%s" % os.getpid()
        channel.queue_declare(queue_name, durable=False)

        properties = pika.BasicProperties()
        properties.headers = {"Hello": "World"}

        try:
            do_basic_publish(channel, queue_name, properties=properties)
            do_basic_get(channel, queue_name)
        finally:
            channel.queue_delete(queue_name)
