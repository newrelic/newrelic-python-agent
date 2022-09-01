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
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper


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
