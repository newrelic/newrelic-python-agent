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
from newrelic.api.time_trace import current_trace, notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)


def _dt_header_injector(transaction, message):
    dt_headers = {k: v.encode("utf-8") for k, v in MessageTrace.generate_request_headers(transaction)}
    # This attribute is a property attribute so it 
    # will always exist but it may not be populated.
    if getattr(message, "application_properties", None):
        message.application_properties.update(dt_headers)
    else:
        message.application_properties = dt_headers


def wrap_ServiceBusSender_init(wrapped, instance, args, kwargs):
    bound_args = bind_args(wrapped, args, kwargs)
    queue_name = bound_args.get("queue_name")
    topic_name = bound_args.get("topic_name")

    if queue_name:
        instance._nr_queue_name = queue_name
    if topic_name:
        instance._nr_topic_name = topic_name
    return wrapped(*args, **kwargs)


def wrap_ServiceBusSender_send_messages(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    transaction.add_messagebroker_info("ServiceBus", get_package_version("azure-servicebus"))
    bound_args = bind_args(wrapped, args, kwargs)
    message = bound_args.get("message")

    destination_type = destination_name = None

    if hasattr(instance, "_nr_queue_name"):
        destination_type = "Queue"
        destination_name = instance._nr_queue_name
        del instance._nr_queue_name
    elif hasattr(instance, "_nr_topic_name"):
        destination_type = "Topic"
        destination_name = instance._nr_topic_name
        del instance._nr_topic_name

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
            return wrapped(*args, **kwargs)
        except Exception:
            notice_error()
            raise

    return wrapped(*args, **kwargs)


def instrument_servicebus_sender(module):
    if hasattr(module, "ServiceBusSender"):
        wrap_function_wrapper(module, "ServiceBusSender.__init__", wrap_ServiceBusSender_init)
        wrap_function_wrapper(module, "ServiceBusSender.send_messages", wrap_ServiceBusSender_send_messages)

