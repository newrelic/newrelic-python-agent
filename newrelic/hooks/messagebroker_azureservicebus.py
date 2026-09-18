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

from newrelic.api.message_trace import MessageTrace

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args


def _dt_header_injector(transaction, message):
    # This seems redundant until we consider that some
    # messages may be deferred, some may be lost, some
    # may be peeked at in another transaction, so each
    # of these messages will get its own DT header.  If
    # they are all received by the same transaction, the
    # logic will be redundant (worst case scenario).
    if isinstance(message, list):
        for msg in message:
            dt_headers = {k: v.encode("utf-8") for k, v in MessageTrace.generate_request_headers(transaction)}
            if getattr(msg, "application_properties", None):
                msg.application_properties.update(dt_headers)
            else:
                msg.application_properties = dt_headers
    else:
        dt_headers = {k: v.encode("utf-8") for k, v in MessageTrace.generate_request_headers(transaction)}
        if getattr(message, "application_properties", None):
            message.application_properties.update(dt_headers)
        else:
            message.application_properties = dt_headers


def _dt_header_acceptor(transaction, message):
    headers = getattr(message, "application_properties", None)
    # The keys and headers get converted to bytes.
    # We need to convert them back to strings.
    string_headers = {k.decode('utf-8'): v.decode('utf-8') for k, v in headers.items()}
    transaction.accept_distributed_trace_headers(string_headers)


def _determine_entity_type(connection_str_or_namespace, entity_name=None):
    from azure.servicebus.management import ServiceBusAdministrationClient
    from azure.core.exceptions import ResourceNotFoundError

    if not entity_name:
        return

    with ServiceBusAdministrationClient.from_connection_string(connection_str_or_namespace) as admin_client:
        try:
            admin_client.get_queue(entity_name)
            return "Queue"
        except ResourceNotFoundError:
            pass

        try:
            admin_client.get_topic(entity_name)
            return "Topic"
        except ResourceNotFoundError:
            pass
            
        return "unknown"


def wrap_ServiceBusSender_init(wrapped, instance, args, kwargs):
    bound_args = bind_args(wrapped, args, kwargs)
    queue_name = bound_args.get("queue_name")
    topic_name = bound_args.get("topic_name")
    entity_name = bound_args.get("entity_name")
    fully_qualified_namespace = bound_args.get("full_qualified_namespace")

    # If entity name was provided instead, determine if this is queue or topic.
    entity_type = _determine_entity_type(fully_qualified_namespace, entity_name)

    if queue_name or (entity_type == "Queue"):
        instance._nr_queue_name = queue_name or entity_name
    elif topic_name or (entity_type == "Topic"):
        instance._nr_topic_name = topic_name or entity_name

    return wrapped(*args, **kwargs)


def wrap_ServiceBusSender_produce_messages(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    transaction.add_messagebroker_info("ServiceBus", get_package_version("azure-servicebus"))
    bound_args = bind_args(wrapped, args, kwargs)
    message = bound_args.get("message") or bound_args.get("messages")

    destination_type = destination_name = None

    if hasattr(instance, "_nr_queue_name"):
        destination_type = "Queue"
        destination_name = instance._nr_queue_name
    elif hasattr(instance, "_nr_topic_name"):
        destination_type = "Topic"
        destination_name = instance._nr_topic_name

    with MessageTrace(
        library="ServiceBus",
        operation="Produce",
        destination_type=destination_type,
        destination_name=destination_name,
        source=wrapped,
    ) as trace:
        try:
            _dt_header_injector(transaction, message)

            host = instance._handler._connection._hostname
            port = instance._handler._connection._port
            trace.agent_attributes.update(
                {
                    "messaging.destination.name": destination_name,
                    "server.address": host,
                    "server.port": port,
                }
            )
        except Exception:
            pass

        return wrapped(*args, **kwargs)


def wrap_ServiceBusSender_cancel_scheduled_messages(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    transaction.add_messagebroker_info("ServiceBus", get_package_version("azure-servicebus"))
    destination_type = destination_name = None

    if hasattr(instance, "_nr_queue_name"):
        destination_type = "Queue"
        destination_name = instance._nr_queue_name
    elif hasattr(instance, "_nr_topic_name"):
        destination_type = "Topic"
        destination_name = instance._nr_topic_name

    with MessageTrace(
        library="ServiceBus",
        operation="Produce",
        destination_type=destination_type,
        destination_name=destination_name,
        source=wrapped,
    ) as trace:
        try:
            host = instance._handler._connection._hostname
            port = instance._handler._connection._port
            trace.agent_attributes.update(
                {
                    "messaging.destination.name": destination_name,
                    "server.address": host,
                    "server.port": port,
                }
            )
            return wrapped(*args, **kwargs)
        except Exception:
            pass

        return wrapped(*args, **kwargs)


def wrap_ServiceBusSender_exit(wrapped, instance, args, kwargs):
    try:
        del instance._nr_queue_name
    except AttributeError:
        pass

    try:
        del instance._nr_topic_name
    except AttributeError:
        pass

    return wrapped(*args, **kwargs)


def wrap_ServiceBusReceiver_init(wrapped, instance, args, kwargs):
    bound_args = bind_args(wrapped, args, kwargs)
    queue_name = bound_args.get("queue_name")
    topic_name = bound_args.get("topic_name")

    result = wrapped(*args, **kwargs)
    entity_name = instance._entity_name
    entity_path = instance.entity_path

    # If entity name was provided instead,
    # determine if this is queue or topic.
    if queue_name or (entity_name == entity_path):
        instance._nr_queue_name = entity_path 
    elif topic_name or (entity_name != entity_path):
        instance._nr_topic_name = entity_path 

    return result


def wrap_build_received_message(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)
    receiver = bound_args.get("receiver")
    entity_name = getattr(receiver, "_entity_name")
    entity_path = getattr(receiver, "_entity_path")

    message = wrapped(*args, **kwargs)

    transaction.add_messagebroker_info("ServiceBus", get_package_version("azure-servicebus"))

    destination_type = "Queue" if (entity_name == entity_path) else "Topic"
    destination_name = entity_path

    with MessageTrace(
        library="ServiceBus",
        operation="Consume",
        destination_type=destination_type,
        destination_name=destination_name,
        terminal=False,
        source=wrapped,
    ) as trace:
        try:
            _dt_header_acceptor(transaction, message)

            host = receiver._handler._connection._hostname
            port = receiver._handler._connection._port
            trace.agent_attributes.update(
                {
                    "messaging.destination.name": destination_name,
                    "server.address": host,
                    "server.port": port,
                }
            )
        except Exception:
            pass

        return message


def wrap_ServiceBusReceiver_peek_messages(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    destination_type = destination_name = None

    if hasattr(instance, "_nr_queue_name"):
        destination_type = "Queue"
        destination_name = instance._nr_queue_name
    elif hasattr(instance, "_nr_topic_name"):
        destination_type = "Topic"
        destination_name = instance._nr_topic_name

    with MessageTrace(
        library="ServiceBus",
        operation="Peek",
        destination_type=destination_type,
        destination_name=destination_name,
        source=wrapped,
    ) as trace:
        try:
            host = instance._handler._connection._hostname
            port = instance._handler._connection._port
            trace.agent_attributes.update(
                {
                    "messaging.destination.name": destination_name,
                    "server.address": host,
                    "server.port": port,
                }
            )
            return wrapped(*args, **kwargs)
        except Exception:
            return wrapped(*args, **kwargs)


def wrap_ServiceBusSender_settle_message_with_retry(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    destination_type = destination_name = None

    if hasattr(instance, "_nr_queue_name"):
        destination_type = "Queue"
        destination_name = instance._nr_queue_name
    elif hasattr(instance, "_nr_topic_name"):
        destination_type = "Topic"
        destination_name = instance._nr_topic_name

    with MessageTrace(
        library="ServiceBus",
        operation="Settle",
        destination_type=destination_type,
        destination_name=destination_name,
        source=wrapped,
    ) as trace:
        try:
            host = instance._handler._connection._hostname
            port = instance._handler._connection._port
            trace.agent_attributes.update(
                {
                    "messaging.destination.name": destination_name,
                    "server.address": host,
                    "server.port": port,
                }
            )
            return wrapped(*args, **kwargs)
        except Exception:
            return wrapped(*args, **kwargs) 


def wrap_ServiceBusReceiver_exit(wrapped, instance, args, kwargs):
    try:
        del instance._nr_queue_name
    except AttributeError:
        pass

    try:
        del instance._nr_topic_name
    except AttributeError:
        pass

    return wrapped(*args, **kwargs)


def instrument_servicebus_sender(module):
    if hasattr(module, "ServiceBusSender"):
        wrap_function_wrapper(module, "ServiceBusSender.__init__", wrap_ServiceBusSender_init)
        wrap_function_wrapper(module, "ServiceBusSender.send_messages", wrap_ServiceBusSender_produce_messages)
        wrap_function_wrapper(module, "ServiceBusSender.schedule_messages", wrap_ServiceBusSender_produce_messages)
        wrap_function_wrapper(module, "ServiceBusSender.cancel_scheduled_messages", wrap_ServiceBusSender_cancel_scheduled_messages)
        wrap_function_wrapper(module, "ServiceBusSender.__exit__", wrap_ServiceBusSender_exit)


def instrument_servicebus_receiver(module):
    if hasattr(module, "ServiceBusReceiver"):
        wrap_function_wrapper(module, "ServiceBusReceiver.__init__", wrap_ServiceBusReceiver_init)
        wrap_function_wrapper(module, "ServiceBusReceiver.peek_messages", wrap_ServiceBusReceiver_peek_messages)
        wrap_function_wrapper(module, "ServiceBusReceiver._settle_message_with_retry", wrap_ServiceBusSender_settle_message_with_retry)
        wrap_function_wrapper(module, "ServiceBusReceiver.__exit__", wrap_ServiceBusReceiver_exit)


def instrument_servicebus_transport_pyamqp_transport(module):
    if hasattr(module, "PyamqpTransport"):
        wrap_function_wrapper(module, "PyamqpTransport.build_received_message", wrap_build_received_message)


def instrument_servicebus_transport_uamqp_transport(module):
    if hasattr(module, "UamqpTransport"):
        wrap_function_wrapper(module, "UamqpTransport.build_received_message", wrap_build_received_message)


