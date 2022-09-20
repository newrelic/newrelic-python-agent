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
import logging
import sys
import time

from newrelic.api.application import application_instance
from newrelic.api.message_trace import MessageTrace
from newrelic.api.message_transaction import MessageTransaction
from newrelic.api.time_trace import current_trace, notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper

_logger = logging.getLogger(__name__)

HEARTBEAT_POLL = "MessageBroker/Kafka/Heartbeat/Poll"
HEARTBEAT_SENT = "MessageBroker/Kafka/Heartbeat/Sent"
HEARTBEAT_FAIL = "MessageBroker/Kafka/Heartbeat/Fail"
HEARTBEAT_RECEIVE = "MessageBroker/Kafka/Heartbeat/Receive"
HEARTBEAT_SESSION_TIMEOUT = "MessageBroker/Kafka/Heartbeat/SessionTimeout"
HEARTBEAT_POLL_TIMEOUT = "MessageBroker/Kafka/Heartbeat/PollTimeout"


def _bind_Producer_produce(topic, value=None, key=None, partition=-1, on_delivery=None, timestamp=0, headers=None):
    return topic, value, key, partition, on_delivery, timestamp, headers


def wrap_Producer_produce(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction is None:
        return wrapped(*args, **kwargs)

    topic, value, key, partition, on_delivery, timestamp, headers = _bind_Producer_produce(*args, **kwargs)
    headers = list(headers) if headers else []

    # Serialization Metrics
    group = "MessageBroker/Kafka/Topic"
    name = "Named/%s" % topic

    if hasattr(instance, "_nr_key_serialization_time"):
        key_serialization_time = instance._nr_key_serialization_time
        if key_serialization_time:
            transaction.record_custom_metric("%s/%s/Serialization/Key" % (group, name), key_serialization_time)
        instance._nr_key_serialization_time = None

    if hasattr(instance, "_nr_value_serialization_time"):
        value_serialization_time = instance._nr_value_serialization_time
        if value_serialization_time:
            transaction.record_custom_metric("%s/%s/Serialization/Value" % (group, name), value_serialization_time)
        instance._nr_value_serialization_time = None

    # Avoid double wrapping with traces for subclasses of Producer
    trace = current_trace()
    if isinstance(trace, MessageTrace):
        return wrapped(*args, **kwargs)

    with MessageTrace(
        library="Kafka",
        operation="Produce",
        destination_type="Topic",
        destination_name=topic or "Default",
        source=wrapped,
    ) as trace:
        dt_headers = [(k, v.encode("utf-8")) for k, v in trace.generate_request_headers(transaction)]
        headers.extend(dt_headers)
        try:
            return wrapped(
                topic,
                value=value,
                key=key,
                partition=partition,
                on_delivery=on_delivery,
                timestamp=timestamp,
                headers=headers,
            )
        except Exception as error:
            # Unwrap kafka errors
            while hasattr(error, "exception"):
                error = error.exception

            _, _, tb = sys.exc_info()
            notice_error((type(error), error, tb))
            tb = None  # Clear reference to prevent reference cycles
            raise


def metric_wrapper(metric_name, check_result=False):
    def _metric_wrapper(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        application = application_instance(activate=False)
        if application:
            if not check_result or check_result and result:
                # If the result does not need validated, send metric.
                # If the result does need validated, ensure it is True.
                application.record_custom_metric(metric_name, 1)

        return result

    return _metric_wrapper


def wrap_Consumer_poll(is_cimpl_wrapper):
    # Hold a flag to determine if this wrapper is applied to the C implementation
    # or to the Python implementation of DeserializingConsumer. Used to differentiate
    # states listed in the comment below.

    def _wrap_Consumer_poll(wrapped, instance, args, kwargs):
        # This wrapper can be called either outside of a transaction, or
        # within the context of an existing transaction.  There are 4
        # possibilities we need to handle: (Note that this is similar to
        # our Pika, Celery, and Kafka-Python instrumentation)
        #
        #   1. Inside an inner wrapper in the DeserializingConsumer
        #
        #       Do nothing. The DeserializingConsumer is double wrapped because
        #       the underlying C implementation is wrapped as well. We need to
        #       detect when the second wrapper is called and ignore it completely
        #       or transactions will be stopped early.
        #
        #   2. In an inactive transaction
        #
        #      If the end_of_transaction() or ignore_transaction() API
        #      calls have been invoked, this iterator may be called in the
        #      context of an inactive transaction. In this case, don't wrap
        #      the iterator in any way. Just run the original iterator.
        #
        #   3. In an active transaction
        #
        #      Do nothing.
        #
        #   4. Outside of a transaction
        #
        #      Since it's not running inside of an existing transaction, we
        #      want to create a new background transaction for it.

        try:
            from confluent_kafka.deserializing_consumer import DeserializingConsumer

            if is_cimpl_wrapper and isinstance(instance, DeserializingConsumer):
                return wrapped(*args, **kwargs)  # Do nothing
        except ImportError:
            return wrapped(*args, **kwargs)

        if hasattr(instance, "_nr_transaction") and not instance._nr_transaction.stopped:
            instance._nr_transaction.__exit__(*sys.exc_info())
            instance._nr_transaction = None

        try:
            record = wrapped(*args, **kwargs)
        except Exception as e:
            notice_error()
            raise

        if record:
            library = "Kafka"
            destination_type = "Topic"
            destination_name = record.topic()
            received_bytes = len(str(record.value()).encode("utf-8"))
            message_count = 1

            headers = record.headers()
            headers = dict(headers) if headers else {}

            transaction = current_transaction(active_only=False)
            if not transaction:
                transaction = MessageTransaction(
                    application=application_instance(),
                    library=library,
                    destination_type=destination_type,
                    destination_name=destination_name,
                    headers=headers,
                    transport_type="Kafka",
                    routing_key=record.key(),
                    source=wrapped,
                )
                instance._nr_transaction = transaction
                transaction.__enter__()

                transaction._add_agent_attribute("kafka.consume.byteCount", received_bytes)

            transaction = current_transaction()

            if transaction:  # If there is an active transaction now.
                # Add metrics whether or not a transaction was already active, or one was just started.
                # Don't add metrics if there was an inactive transaction.
                # Name the metrics using the same format as the transaction, but in case the active transaction
                # was an existing one and not a message transaction, reproduce the naming logic here.
                group = "Message/%s/%s" % (library, destination_type)
                name = "Named/%s" % destination_name
                transaction.record_custom_metric("%s/%s/Received/Bytes" % (group, name), received_bytes)
                transaction.record_custom_metric("%s/%s/Received/Messages" % (group, name), message_count)

                # Deserialization Metrics
                if hasattr(instance, "_nr_key_deserialization_time"):
                    key_deserialization_time = instance._nr_key_deserialization_time
                    if key_deserialization_time:
                        transaction.record_custom_metric(
                            "%s/%s/Deserialization/Key" % (group, name), key_deserialization_time
                        )
                    instance._nr_key_deserialization_time = None

                if hasattr(instance, "_nr_value_deserialization_time"):
                    value_deserialization_time = instance._nr_value_deserialization_time
                    if value_deserialization_time:
                        transaction.record_custom_metric(
                            "%s/%s/Deserialization/Value" % (group, name), value_deserialization_time
                        )
                    instance._nr_value_deserialization_time = None

        return record

    return _wrap_Consumer_poll


def serializer_wrapper(client, key):
    @function_wrapper
    def _serializer_wrapper(wrapped, instance, args, kwargs):
        start_time = time.time()
        result = wrapped(*args, **kwargs)

        try:
            setattr(client, key, (time.time() - start_time))
        except Exception:
            # Don't raise errors if object is immutable
            pass

        return result

    return _serializer_wrapper


def wrap_SerializingProducer_init(wrapped, instance, args, kwargs):
    wrapped(*args, **kwargs)

    if hasattr(instance, "_key_serializer") and callable(instance._key_serializer):
        instance._key_serializer = serializer_wrapper(instance, "_nr_key_serialization_time")(instance._key_serializer)

    if hasattr(instance, "_value_serializer") and callable(instance._value_serializer):
        instance._value_serializer = serializer_wrapper(instance, "_nr_value_serialization_time")(
            instance._value_serializer
        )


def wrap_DeserializingConsumer_init(wrapped, instance, args, kwargs):
    wrapped(*args, **kwargs)

    if hasattr(instance, "_key_deserializer") and callable(instance._key_deserializer):
        instance._key_deserializer = serializer_wrapper(instance, "_nr_key_deserialization_time")(
            instance._key_deserializer
        )

    if hasattr(instance, "_value_deserializer") and callable(instance._value_deserializer):
        instance._value_deserializer = serializer_wrapper(instance, "_nr_value_deserialization_time")(
            instance._value_deserializer
        )


def wrap_immutable_class(module, class_name):
    # Wrap immutable binary extension class with a mutable Python subclass
    new_class = type(class_name, (getattr(module, class_name),), {})
    setattr(module, class_name, new_class)
    return new_class


def instrument_confluentkafka_cimpl(module):
    if hasattr(module, "Producer"):
        wrap_immutable_class(module, "Producer")
        wrap_function_wrapper(module, "Producer.produce", wrap_Producer_produce)

    if hasattr(module, "Consumer"):
        wrap_immutable_class(module, "Consumer")
        wrap_function_wrapper(module, "Consumer.poll", wrap_Consumer_poll(is_cimpl_wrapper=True))


def instrument_confluentkafka_serializing_producer(module):
    if hasattr(module, "SerializingProducer"):
        wrap_function_wrapper(module, "SerializingProducer.__init__", wrap_SerializingProducer_init)
        wrap_function_wrapper(module, "SerializingProducer.produce", wrap_Producer_produce)


def instrument_confluentkafka_deserializing_consumer(module):
    if hasattr(module, "DeserializingConsumer"):
        wrap_function_wrapper(module, "DeserializingConsumer.__init__", wrap_DeserializingConsumer_init)
        wrap_function_wrapper(module, "DeserializingConsumer.poll", wrap_Consumer_poll(is_cimpl_wrapper=False))
