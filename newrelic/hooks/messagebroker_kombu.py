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

from newrelic.api.application import application_instance, application_settings
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.message_transaction import MessageTransaction
from newrelic.api.time_trace import current_trace, notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)

"""
The following are unsupported transport types since the libraries are too old:
* librabbitmq
* qpid
* amqp uses librabbitmq or py-amqp
"""
AVAILABLE_TRANSPORTS = {
    "py-amqp": "AMQP",
    "sqs": "SQS",
    "redis": "REDIS",
    "zookeeper": "ZooKeeper",
    "confluentkafka": "Kafka",
}


def bind_publish(
    body,
    routing_key=None,
    delivery_mode=None,
    mandatory=False,
    immediate=False,
    priority=0,
    content_type=None,
    content_encoding=None,
    serializer=None,
    headers=None,
    compression=None,
    exchange=None,
    retry=False,
    retry_policy=None,
    declare=None,
    expiration=None,
    timeout=None,
    confirm_timeout=None,
    **properties,
):
    return {
        "body": body,
        "routing_key": routing_key,
        "delivery_mode": delivery_mode,
        "mandatory": mandatory,
        "immediate": immediate,
        "priority": priority,
        "content_type": content_type,
        "content_encoding": content_encoding,
        "serializer": serializer,
        "headers": headers,
        "compression": compression,
        "exchange": exchange,
        "retry": retry,
        "retry_policy": retry_policy,
        "declare": declare,
        "expiration": expiration,
        "timeout": timeout,
        "confirm_timeout": confirm_timeout,
        "properties": properties,
    }


def wrap_Producer_publish(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    try:
        bound_args = bind_publish(*args, **kwargs)
    except Exception:
        _logger.debug(
            "Unable to bind arguments for kombu.messaging.Producer.publish. Report this issue to New Relic support.",
            record_exception=True,
        )
        return wrapped(*args, **kwargs)

    headers = bound_args["headers"]
    headers = headers if headers else {}
    exchange = getattr(bound_args["exchange"], "name", None) or "Default"

    transaction.add_messagebroker_info("Kombu", get_package_version("kombu"))

    with MessageTrace(
        library="Kombu",
        operation="Produce",
        destination_type="Exchange",
        destination_name=exchange,
        source=wrapped,
        terminal=False,
    ):
        dt_headers = {k: v.encode("utf-8") for k, v in MessageTrace.generate_request_headers(transaction)}
        if headers:
            dt_headers.update(headers)

        try:
            bound_args["headers"] = dt_headers
            return wrapped(**bound_args)
        except Exception:
            notice_error()
            raise


def wrap_consumer_recieve_callback(wrapped, instance, args, kwargs):
    # In cases where Kombu is being used to talk to the queue via Celery (aka Celery
    # is the toplevel api) a transaction will be created for Kombu and a separate
    # transaction will be created for Celery. If instrumentation.kombu.consumer.enabled
    # is disabled, do not create the duplicate Kombu transaction.
    settings = application_settings() or global_settings()
    if not settings.instrumentation.kombu.consumer.enabled:
        return wrapped(*args, **kwargs)

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
        destination_name = getattr(message, "delivery_info", {}).get("exchange") or "Default"
        received_bytes = len(str(body).encode("utf-8"))
        message_count = 1
        transaction = current_transaction(active_only=False)
        if not transaction and destination_name not in settings.instrumentation.kombu.ignored_exchanges:
            # Try to get the transport type. The default for kombu is py-amqp.
            # If not in the known transport type list, fallback to "Other".
            try:
                transport_name = getattr(
                    getattr(getattr(instance, "connection", None), "transport", None), "driver_name", "py-amqp"
                )
                transport_type = AVAILABLE_TRANSPORTS.get(transport_name.lower(), "Other")
            except Exception:
                _logger.debug("Failed to determine transport type.", exc_info=True)
                transport_type = "Other"
            created_transaction = MessageTransaction(
                application=application_instance(),
                library=library,
                destination_type=destination_type,
                destination_name=destination_name,
                headers=dict(getattr(message, "headers", {})),
                transport_type=transport_type,
                routing_key=key,
                source=wrapped,
            )
            created_transaction.__enter__()

            # Obtain consumer client_id to send up as agent attribute
            if hasattr(message, "channel") and hasattr(message.channel, "channel_id"):
                channel_id = message.channel.channel_id
                created_transaction._add_agent_attribute("kombu.consume.channel_id", channel_id)
            if received_bytes:
                created_transaction._add_agent_attribute("kombu.consume.byteCount", received_bytes)

        transaction = current_transaction()
        if transaction:  # If there is an active transaction now.
            # Add metrics whether or not a transaction was already active, or one was just started.
            # Don't add metrics if there was an inactive transaction.
            # Name the metrics using the same format as the transaction, but in case the active transaction
            # was an existing one and not a message transaction, reproduce the naming logic here.
            group = f"Message/{library}/{destination_type}"
            name = f"Named/{destination_name}"
            if received_bytes:
                transaction.record_custom_metric(f"{group}/{name}/Received/Bytes", received_bytes)
            if message_count:
                transaction.record_custom_metric(f"{group}/{name}/Received/Messages", message_count)
            transaction.add_messagebroker_info("Kombu", get_package_version("kombu"))

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        if created_transaction:
            created_transaction.__exit__(*sys.exc_info())
        elif current_transaction():
            # Report error on existing transaction if there is one
            notice_error()
        else:
            # Report error on application
            notice_error(application=application_instance(activate=False))
        raise

    if created_transaction and not created_transaction.stopped:
        created_transaction.__exit__(*sys.exc_info())

    return return_val


def wrap_serialize(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    exchange = "Unknown"
    if isinstance(transaction, MessageTransaction):
        exchange = transaction.destination_name
    else:
        # Find parent message trace to retrieve topic
        message_trace = current_trace()
        while message_trace is not None and not isinstance(message_trace, MessageTrace):
            message_trace = message_trace.parent
        if message_trace:
            exchange = message_trace.destination_name

    group = "MessageBroker/Kombu/Exchange"
    name = f"Named/{exchange}/Serialization/Value"

    with FunctionTrace(name=name, group=group):
        return wrapped(*args, **kwargs)


def instrument_kombu_messaging(module):
    if hasattr(module, "Producer"):
        wrap_function_wrapper(module, "Producer.publish", wrap_Producer_publish)
    if hasattr(module, "Consumer"):
        wrap_function_wrapper(module, "Consumer._receive_callback", wrap_consumer_recieve_callback)
    # This is a little unorthodox but because Kombu creates an object on import we
    # have to instrument it where it's used/imported as opposed to where the class is
    # defined.
    if hasattr(module, "dumps"):
        wrap_function_wrapper(module, "dumps", wrap_serialize)


def instrument_kombu_serializaion(module):
    # This is a little unorthodox but because Kombu creates an object on import we
    # have to instrument it where it's used/imported as opposed to where the class is
    # defined.
    if hasattr(module, "loads"):
        wrap_function_wrapper(module, "loads", wrap_serialize)
