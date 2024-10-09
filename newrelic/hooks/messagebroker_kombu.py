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
import sys

from newrelic.api.application import application_instance
from newrelic.api.function_trace import FunctionTraceWrapper
from newrelic.api.message_trace import MessageTrace
from newrelic.api.message_transaction import MessageTransaction
from newrelic.api.time_trace import current_trace, notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import (
    ObjectProxy,
    function_wrapper,
    wrap_function_wrapper,
)
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args

HEARTBEAT_POLL = "MessageBroker/Kafka/Heartbeat/Poll"
HEARTBEAT_SENT = "MessageBroker/Kafka/Heartbeat/Sent"
HEARTBEAT_FAIL = "MessageBroker/Kafka/Heartbeat/Fail"
HEARTBEAT_RECEIVE = "MessageBroker/Kafka/Heartbeat/Receive"
HEARTBEAT_SESSION_TIMEOUT = "MessageBroker/Kafka/Heartbeat/SessionTimeout"
HEARTBEAT_POLL_TIMEOUT = "MessageBroker/Kafka/Heartbeat/PollTimeout"


def _bind_send(
    topic, value=None, key=None, headers=None, partition=None, timestamp_ms=None
):
    return topic, value, key, headers, partition, timestamp_ms


def wrap_Producer_publish(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)
    headers = bound_args["headers"]
    headers = headers if headers else {}
    value = bound_args["body"]
    key = bound_args["routing_key"]
    exchange = getattr(bound_args["exchange"], "name", "Default")

    transaction.add_messagebroker_info("Kombu", get_package_version("kombu"))

    with MessageTrace(
        library="Kombu",
        operation="Produce",
        destination_type="Exchange",
        destination_name=exchange,
        source=wrapped,
        terminal=False,
    ):
        dt_headers = {
            k: v.encode("utf-8")
            for k, v in MessageTrace.generate_request_headers(transaction)
        }
        # headers can be a list of tuples or a dict so convert to dict for consistency.
        if headers:
            dt_headers.update(headers)

        # instance.connection.host
        # if hasattr(instance, "config"):
        #    for server_name in instance.config.get("bootstrap_servers", []):
        #        transaction.record_custom_metric(f"MessageBroker/Kafka/Nodes/{server_name}/Produce/{topic}", 1)
        try:
            bound_args["headers"] = dt_headers
            return wrapped(**bound_args)
        except Exception:
            notice_error()
            raise


def wrap_consumer_recieve_callback(wrapped, instance, args, kwargs):
    # This will be the transaction if any that is created by this wrapper.
    created_transaction = None

    bound_args = bind_args(wrapped, args, kwargs)
    message = bound_args["message"]
    if message:
        # In Kombu there is not iterator, instead there is a callback that
        # is called inside wrapped.
        # This callback can be called either outside of a transaction, or
        # within the context of an existing transaction.  There are 3
        # possibilities we need to handle: (Note that this is similar to
        # our Pika and Celery instrumentation)
        #
        #   1. In an inactive transaction
        #
        #      If the end_of_transaction() or ignore_transaction() API
        #      calls have been invoked, this iterator may be called in the
        #      context of an inactive transaction. In this case, don't wrap
        #      the callback in any way.
        #
        #   2. In an active transaction
        #
        #      Do nothing.
        #
        #   3. Outside of a transaction
        #
        #      Since it's not running inside of an existing transaction, we
        #      want to create a new background transaction for it.
        body = getattr(message, "body", None)
        key = getattr(message, "delivery_info", {}).get("routing_key")
        library = "Kombu"
        destination_type = "Exchange"
        destination_name = getattr(message, "delivery_info", {}).get("exchange")
        value = len(str(body).encode("utf-8"))
        message_count = 1
        received_bytes = getattr(message, "body_received", None)

        transaction = current_transaction(active_only=False)
        if not transaction:
            created_transaction = MessageTransaction(
                application=application_instance(),
                library=library,
                destination_type=destination_type,
                destination_name=destination_name,
                headers=dict(getattr(message, "headers", {})),
                transport_type="AMQP",
                routing_key=key,
                source=wrapped,
            )
            created_transaction.__enter__()  # pylint: disable=C2801

            # Obtain consumer client_id to send up as agent attribute
            if hasattr(message, "channel") and hasattr(message.channel, "channel_id"):
                channel_id = message.channel.channel_id
                created_transaction._add_agent_attribute(
                    "kombu.consume.channel_id", channel_id
                )
            created_transaction._add_agent_attribute(
                "kombu.consume.byteCount", received_bytes
            )

        transaction = current_transaction()
        if transaction:  # If there is an active transaction now.
            # Add metrics whether or not a transaction was already active, or one was just started.
            # Don't add metrics if there was an inactive transaction.
            # Name the metrics using the same format as the transaction, but in case the active transaction
            # was an existing one and not a message transaction, reproduce the naming logic here.
            group = f"Message/{library}/{destination_type}"
            name = f"Named/{destination_name}"
            transaction.record_custom_metric(
                f"{group}/{name}/Received/Bytes", received_bytes
            )
            transaction.record_custom_metric(
                f"{group}/{name}/Received/Messages", message_count
            )
            # if hasattr(instance, "config"):
            #    for server_name in instance.config.get("bootstrap_servers", []):
            #        transaction.record_custom_metric(
            #            f"MessageBroker/Kafka/Nodes/{server_name}/Consume/{destination_name}", 1
            #        )
            transaction.add_messagebroker_info("Kombu", get_package_version("kombu"))

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        if current_transaction():
            # Report error on existing transaction if there is one
            notice_error()
        else:
            # Report error on application
            notice_error(application=application_instance(activate=False))
        raise

    if created_transaction and not created_transaction.stopped:
        created_transaction.__exit__(*sys.exc_info())

    return return_val


def wrap_Producer_init(wrapped, instance, args, kwargs):
    get_config_key = lambda key: kwargs.get(key, instance.DEFAULT_CONFIG[key])  # pylint: disable=C3001 # noqa: E731

    kwargs["key_serializer"] = wrap_serializer(
        instance, "Serialization/Key", "MessageBroker", get_config_key("key_serializer")
    )
    kwargs["value_serializer"] = wrap_serializer(
        instance,
        "Serialization/Value",
        "MessageBroker",
        get_config_key("value_serializer"),
    )

    return wrapped(*args, **kwargs)


class NewRelicSerializerWrapper(ObjectProxy):
    def __init__(self, wrapped, serializer_name, group_prefix):
        ObjectProxy.__init__.__get__(self)(wrapped)  # pylint: disable=W0231

        self._nr_serializer_name = serializer_name
        self._nr_group_prefix = group_prefix

    def serialize(self, topic, object):
        wrapped = self.__wrapped__.serialize  # pylint: disable=W0622
        args = (topic, object)
        kwargs = {}

        if not current_transaction():
            return wrapped(*args, **kwargs)

        group = f"{self._nr_group_prefix}/Kafka/Topic"
        name = f"Named/{topic}/{self._nr_serializer_name}"

        return FunctionTraceWrapper(wrapped, name=name, group=group)(*args, **kwargs)


def wrap_serializer(client, serializer_name, group_prefix, serializer):
    @function_wrapper
    def _wrap_serializer(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        topic = "Unknown"
        if isinstance(transaction, MessageTransaction):
            topic = transaction.destination_name
        else:
            # Find parent message trace to retrieve topic
            message_trace = current_trace()
            while message_trace is not None and not isinstance(
                message_trace, MessageTrace
            ):
                message_trace = message_trace.parent
            if message_trace:
                topic = message_trace.destination_name

        group = f"{group_prefix}/Kafka/Topic"
        name = f"Named/{topic}/{serializer_name}"

        return FunctionTraceWrapper(wrapped, name=name, group=group)(*args, **kwargs)

    try:
        # Apply wrapper to serializer
        if serializer is None:
            # Do nothing
            return serializer
        elif isinstance(serializer, Serializer):
            return NewRelicSerializerWrapper(
                serializer, group_prefix=group_prefix, serializer_name=serializer_name
            )
        else:
            # Wrap callable in wrapper
            return _wrap_serializer(serializer)
    except Exception:
        return serializer  # Avoid crashes from immutable serializers


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


def instrument_kombu_messaging(module):
    if hasattr(module, "Producer"):
        # wrap_function_wrapper(module, "Producer.__init__", wrap_Producer_init)
        wrap_function_wrapper(module, "Producer.publish", wrap_Producer_publish)
    if hasattr(module, "Consumer"):
        wrap_function_wrapper(
            module, "Consumer._receive_callback", wrap_consumer_recieve_callback
        )


def instrument_kombu_heartbeat(module):
    if hasattr(module, "Heartbeat"):
        if hasattr(module.Heartbeat, "poll"):
            wrap_function_wrapper(
                module, "Heartbeat.poll", metric_wrapper(HEARTBEAT_POLL)
            )

        if hasattr(module.Heartbeat, "fail_heartbeat"):
            wrap_function_wrapper(
                module, "Heartbeat.fail_heartbeat", metric_wrapper(HEARTBEAT_FAIL)
            )

        if hasattr(module.Heartbeat, "sent_heartbeat"):
            wrap_function_wrapper(
                module, "Heartbeat.sent_heartbeat", metric_wrapper(HEARTBEAT_SENT)
            )

        if hasattr(module.Heartbeat, "received_heartbeat"):
            wrap_function_wrapper(
                module,
                "Heartbeat.received_heartbeat",
                metric_wrapper(HEARTBEAT_RECEIVE),
            )

        if hasattr(module.Heartbeat, "session_timeout_expired"):
            wrap_function_wrapper(
                module,
                "Heartbeat.session_timeout_expired",
                metric_wrapper(HEARTBEAT_SESSION_TIMEOUT, check_result=True),
            )

        if hasattr(module.Heartbeat, "poll_timeout_expired"):
            wrap_function_wrapper(
                module,
                "Heartbeat.poll_timeout_expired",
                metric_wrapper(HEARTBEAT_POLL_TIMEOUT, check_result=True),
            )
