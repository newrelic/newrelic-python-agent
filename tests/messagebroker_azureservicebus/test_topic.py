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
import datetime

from azure.servicebus import ServiceBusMessage
from azure.servicebus.amqp import AmqpAnnotatedMessage

from newrelic.api.background_task import background_task
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


def test_topic_send_and_receive(topic_name, subscription_name, topic_sender, subscription_receiver):
    _metrics = [
        (f"MessageBroker/ServiceBus/Topic/Produce/Named/{topic_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Peek/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Consume/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Settle/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_send_and_receive.<locals>._test",
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        message_text = "Send message from topic."
        sent_message = ServiceBusMessage(message_text)
        topic_sender.send_messages(sent_message)

        received_peek_messages = subscription_receiver.peek_messages(max_message_count=1)
        for message in received_peek_messages:
            message_body = message._message.data[0].decode()
            assert message_body == message_text

        received_messages = subscription_receiver.receive_messages(max_message_count=1, max_wait_time=5)
        for message in received_messages:
            message_body = message._message.data[0].decode()
            assert message_body == message_text
            subscription_receiver.complete_message(message)

    _test()


def test_topic_schedule_and_cancel(topic_name, topic_sender):
    _metrics = [
        (f"MessageBroker/ServiceBus/Topic/Produce/Named/{topic_name}", 2),
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_schedule_and_cancel.<locals>._test",
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        message_text = "Schedule message from topic."
        sent_message = ServiceBusMessage(message_text)
        scheduled_time_utc = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=30)
        sequence_number = topic_sender.schedule_messages(sent_message, scheduled_time_utc)
        topic_sender.cancel_scheduled_messages(sequence_number)

    _test()


def test_topic_send_and_receive_deferred_message(topic_name, subscription_name, topic_sender, subscription_receiver):
    _metrics = [
        (f"MessageBroker/ServiceBus/Topic/Produce/Named/{topic_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Consume/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Settle/Named/{topic_name}/Subscriptions/{subscription_name}", 2),
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_send_and_receive_deferred_message.<locals>._test",
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        message_text = "Send message from topic to be deferred."
        sent_message = ServiceBusMessage(message_text)
        topic_sender.send_messages(sent_message)

        received_messages = subscription_receiver.receive_messages(max_message_count=1, max_wait_time=5)
        for message in received_messages:
            message_body = message._message.data[0].decode()
            assert message_body == message_text
            sequence_number = message.sequence_number
            subscription_receiver.defer_message(message)

        received_deferred_messages = subscription_receiver.receive_deferred_messages(sequence_numbers=sequence_number)
        for message in received_deferred_messages:
            message_body = message._message.data[0].decode()
            assert message_body == message_text
            subscription_receiver.complete_message(message)

    _test()

    
def test_topic_send_and_receive_dead_letter_message(topic_name, subscription_name, topic_sender, subscription_receiver, subscription_dead_letter_receiver):
    _metrics = [
        (f"MessageBroker/ServiceBus/Topic/Produce/Named/{topic_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Consume/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Settle/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_send_and_receive_dead_letter_message.<locals>._test",
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        message_text = "Send message from topic to dead letter subscription."
        sent_message = ServiceBusMessage(message_text)
        topic_sender.send_messages(sent_message)

        received_messages = subscription_receiver.receive_messages(max_message_count=1, max_wait_time=5)
        for message in received_messages:
            message_body = message._message.data[0].decode()
            assert message_body == message_text
            subscription_receiver.dead_letter_message(message)

        received_dead_letter_messages = subscription_dead_letter_receiver.receive_messages(max_message_count=1, max_wait_time=5)
        for message in received_dead_letter_messages:
            message_body = message._message.data[0].decode()
            assert message_body == message_text
            subscription_dead_letter_receiver.complete_message(message)

    _test()


def test_topic_send_and_receive_AmqpAnnotatedMessage(topic_name, subscription_name, topic_sender, subscription_receiver):
    _metrics = [
        (f"MessageBroker/ServiceBus/Topic/Produce/Named/{topic_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Consume/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Settle/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_send_and_receive_AmqpAnnotatedMessage.<locals>._test",
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        message_text = "Send AmqpAnnotatedMessage message type from topic."
        application_properties = {"body_type": "data"}
        delivery_annotations = {"delivery_annotation_key": "value"}
        sent_message = AmqpAnnotatedMessage(data_body=message_text, delivery_annotations=delivery_annotations, application_properties=application_properties)
        topic_sender.send_messages(sent_message)

        received_messages = subscription_receiver.receive_messages(max_message_count=1, max_wait_time=5)
        for message in received_messages:
            message_body = message.raw_amqp_message._data_body[0].decode()
            assert message_body == message_text
            subscription_receiver.complete_message(message)

    _test()


def test_topic_send_and_receive_multiple_messages(topic_name, subscription_name, topic_sender, subscription_receiver):
    _metrics = [
        (f"MessageBroker/ServiceBus/Topic/Produce/Named/{topic_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Consume/Named/{topic_name}/Subscriptions/{subscription_name}", 2),
        (f"MessageBroker/ServiceBus/Topic/Settle/Named/{topic_name}/Subscriptions/{subscription_name}", 2),
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_send_and_receive_multiple_messages.<locals>._test",
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        messages_text = ["Send message from topic.", "Send a second message from topic"]
        sent_messages = list(map(ServiceBusMessage, messages_text))
        topic_sender.send_messages(sent_messages)

        received_messages = subscription_receiver.receive_messages(max_message_count=2, max_wait_time=5)
        for message in received_messages:
            message_body = message._message.data[0].decode()
            assert message_body in messages_text
            subscription_receiver.complete_message(message)

    _test()


def test_topic_distributed_traces_one_sent_one_received(topic_name, subscription_name, topic_sender, subscription_receiver):
    """
    Send operation gets one transaction and receive operation gets another
    transaction.  Two items are sent, so DT header is sent for each item.
    Since one transaction is receiving both items, we only need to read a
    header from the first item in order to connect the two transactions.
    """
    _send_scoped_metrics = [
        (f"MessageBroker/ServiceBus/Topic/Produce/Named/{topic_name}", 1),
    ]
    _send_rollup_metrics = [
        ("Supportability/TraceContext/Create/Success", 2),
        *_send_scoped_metrics,
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_distributed_traces_one_sent_one_received.<locals>._send",
        scoped_metrics=_send_scoped_metrics,
        rollup_metrics=_send_rollup_metrics,
        background_task=True,
    )
    @background_task()
    def _send():
        messages_text = ["Send message from topic.", "Send a second message from topic"]
        sent_messages = list(map(ServiceBusMessage, messages_text))
        topic_sender.send_messages(sent_messages)

    _receive_scoped_metrics = [
        (f"MessageBroker/ServiceBus/Topic/Consume/Named/{topic_name}/Subscriptions/{subscription_name}", 2),
        (f"MessageBroker/ServiceBus/Topic/Settle/Named/{topic_name}/Subscriptions/{subscription_name}", 2),
    ]
    _receive_rollup_metrics = [
        ("Supportability/TraceContext/TraceParent/Accept/Success", 1),
        ("Supportability/TraceContext/Accept/Success", 1),
        *_receive_scoped_metrics,
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_distributed_traces_one_sent_one_received.<locals>._receive",
        scoped_metrics=_receive_scoped_metrics,
        rollup_metrics=_receive_rollup_metrics,
        background_task=True,
    )
    @background_task()
    def _receive():
        received_messages = subscription_receiver.receive_messages(max_message_count=2, max_wait_time=5)
        for message in received_messages:
            subscription_receiver.complete_message(message)

    _send()
    _receive()


def test_topic_distributed_traces_one_sent_two_received(topic_name, subscription_name, topic_sender, subscription_receiver):
    """
    Send operation gets one transaction and two separate transactions
    are used for receiving of one item.  Two items are sent, so DT header
    is sent for each item.  Now, each receiving transaction should
    receive a DT header for the one item that they received.
    """
    _send_scoped_metrics = [
        (f"MessageBroker/ServiceBus/Topic/Produce/Named/{topic_name}", 1),
    ]
    _send_rollup_metrics = [
        ("Supportability/TraceContext/Create/Success", 2),
        *_send_scoped_metrics,
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_distributed_traces_one_sent_two_received.<locals>._send",
        scoped_metrics=_send_scoped_metrics,
        rollup_metrics=_send_rollup_metrics,
        background_task=True,
    )
    @background_task()
    def _send():
        messages_text = ["Send message from topic.", "Send a second message from topic"]
        sent_messages = list(map(ServiceBusMessage, messages_text))
        topic_sender.send_messages(sent_messages)


    _receive1_scoped_metrics = [
        (f"MessageBroker/ServiceBus/Topic/Consume/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Settle/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
    ]
    _receive1_rollup_metrics = [
        ("Supportability/TraceContext/TraceParent/Accept/Success", 1),
        ("Supportability/TraceContext/Accept/Success", 1),
        *_receive1_scoped_metrics,
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_distributed_traces_one_sent_two_received.<locals>._receive1",
        scoped_metrics=_receive1_scoped_metrics,
        rollup_metrics=_receive1_rollup_metrics,
        background_task=True,
    )
    @background_task()
    def _receive1():
        received_messages = subscription_receiver.receive_messages(max_message_count=1, max_wait_time=5)
        for message in received_messages:
            subscription_receiver.complete_message(message)


    _receive2_scoped_metrics = [
        (f"MessageBroker/ServiceBus/Topic/Consume/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Settle/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
    ]
    _receive2_rollup_metrics = [
        ("Supportability/TraceContext/TraceParent/Accept/Success", 1),
        ("Supportability/TraceContext/Accept/Success", 1),
        *_receive2_scoped_metrics,
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_distributed_traces_one_sent_two_received.<locals>._receive2",
        scoped_metrics=_receive2_scoped_metrics,
        rollup_metrics=_receive2_rollup_metrics,
        background_task=True,
    )
    @background_task()
    def _receive2():
        received_messages = subscription_receiver.receive_messages(max_message_count=1, max_wait_time=5)
        for message in received_messages:
            subscription_receiver.complete_message(message)


    _send()
    _receive1()
    _receive2()


@pytest.mark.skip(reason="Emulator does not support this")
def test_topic_send_and_receive_iterative(topic_name, subscription_name, topic_sender, subscription_receiver):
    """
    This tests receiving a message iteratively, i.e.
    without explicitly using `receiver.receive_messages()`
    NOTE: This test works with an Azure instance
    but the emulator used to run this does not.
    """

    _metrics = [
        (f"MessageBroker/ServiceBus/Topic/Produce/Named/{topic_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Peek/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Consume/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
        (f"MessageBroker/ServiceBus/Topic/Settle/Named/{topic_name}/Subscriptions/{subscription_name}", 1),
    ]

    @validate_transaction_metrics(
        "test_topic:test_topic_send_and_receive_iterative.<locals>._test",
        scoped_metrics=_metrics,
        rollup_metrics=_metrics,
        background_task=True,
    )
    @background_task()
    def _test():
        messages_text = ["Send message from topic.", "Send a second message from topic"]
        sent_messages = list(map(ServiceBusMessage, messages_text))
        topic_sender.send_messages(sent_messages)

        for message in subscription_receiver:
            message_body = message._message.data[0].decode()
            assert message_body in messages_text
            subscription_receiver.complete_message(message)

    _test()





