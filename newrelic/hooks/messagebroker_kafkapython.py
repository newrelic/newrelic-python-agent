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

from newrelic.api.application import application_instance
from newrelic.api.message_trace import MessageTrace
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper

HEARTBEAT_POLL = "MessageBroker/Kafka/Heartbeat/Poll"
HEARTBEAT_SENT = "MessageBroker/Kafka/Heartbeat/Sent"
HEARTBEAT_FAIL = "MessageBroker/Kafka/Heartbeat/Fail"
HEARTBEAT_RECEIVE = "MessageBroker/Kafka/Heartbeat/Receive"
HEARTBEAT_SESSION_TIMEOUT = "MessageBroker/Kafka/Heartbeat/SessionTimeout"
HEARTBEAT_POLL_TIMEOUT = "MessageBroker/Kafka/Heartbeat/PollTimeout"


def _bind_send(topic, value=None, key=None, headers=None, partition=None, timestamp_ms=None):
    return topic, value, key, headers, partition, timestamp_ms


def wrap_KafkaProducer_send(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    topic, value, key, headers, partition, timestamp_ms = _bind_send(*args, **kwargs)
    headers = list(headers) if headers else []

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
            return wrapped(topic, value=value, key=key, headers=headers, partition=partition, timestamp_ms=timestamp_ms)
        except Exception:
            notice_error()
            raise


def instrument_kafka_producer(module):
    if hasattr(module, "KafkaProducer"):
        wrap_function_wrapper(module, "KafkaProducer.send", wrap_KafkaProducer_send)


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


def instrument_kafka_heartbeat(module):
    if hasattr(module, "Heartbeat"):
        if hasattr(module.Heartbeat, "poll"):
            wrap_function_wrapper(module, "Heartbeat.poll", metric_wrapper(HEARTBEAT_POLL))

        if hasattr(module.Heartbeat, "fail_heartbeat"):
            wrap_function_wrapper(module, "Heartbeat.fail_heartbeat", metric_wrapper(HEARTBEAT_FAIL))

        if hasattr(module.Heartbeat, "sent_heartbeat"):
            wrap_function_wrapper(module, "Heartbeat.sent_heartbeat", metric_wrapper(HEARTBEAT_SENT))

        if hasattr(module.Heartbeat, "received_heartbeat"):
            wrap_function_wrapper(module, "Heartbeat.received_heartbeat", metric_wrapper(HEARTBEAT_RECEIVE))

        if hasattr(module.Heartbeat, "session_timeout_expired"):
            wrap_function_wrapper(
                module,
                "Heartbeat.session_timeout_expired",
                metric_wrapper(HEARTBEAT_SESSION_TIMEOUT, check_result=True),
            )

        if hasattr(module.Heartbeat, "poll_timeout_expired"):
            wrap_function_wrapper(
                module, "Heartbeat.poll_timeout_expired", metric_wrapper(HEARTBEAT_POLL_TIMEOUT, check_result=True)
            )
