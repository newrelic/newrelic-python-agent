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

from kafka.serializer import Serializer

from newrelic.api.application import application_instance
from newrelic.api.function_trace import FunctionTraceWrapper
from newrelic.api.message_trace import MessageTrace
from newrelic.api.message_transaction import MessageTransaction
from newrelic.api.time_trace import current_trace, notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy, function_wrapper, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

HEARTBEAT_POLL = "MessageBroker/Kafka/Heartbeat/Poll"
HEARTBEAT_SENT = "MessageBroker/Kafka/Heartbeat/Sent"
HEARTBEAT_FAIL = "MessageBroker/Kafka/Heartbeat/Fail"
HEARTBEAT_RECEIVE = "MessageBroker/Kafka/Heartbeat/Receive"
HEARTBEAT_SESSION_TIMEOUT = "MessageBroker/Kafka/Heartbeat/SessionTimeout"
HEARTBEAT_POLL_TIMEOUT = "MessageBroker/Kafka/Heartbeat/PollTimeout"

KAFKA_CLUSTER_METRIC_PRODUCE = "MessageBroker/Kafka/Cluster/{0}/Produce/{1}"
KAFKA_CLUSTER_METRIC_CONSUME = "MessageBroker/Kafka/Cluster/{0}/Consume/{1}"

_logger = logging.getLogger(__name__)


def _cluster_metrics_enabled():
    settings = global_settings()
    return bool(getattr(getattr(settings, "kafka", None), "cluster_metrics_enabled", False))


def _read_cluster_id(instance):
    # ClusterMetadata.update_metadata() receives the cluster id on every real
    # metadata refresh (it's a field on the raw MetadataResponse) but discards it —
    # it only copies brokers/topics/controller_id onto self. wrap_ClusterMetadata_update_metadata
    # captures it into _nr_cluster_id as a passive side effect of that same refresh,
    # so this read stays a synchronous, in-memory attribute lookup: no admin client,
    # no extra connection. KafkaProducer and KafkaConsumer expose the ClusterMetadata
    # object via different attribute paths.
    if not _cluster_metrics_enabled():
        return None
    metadata = getattr(instance, "_metadata", None)  # KafkaProducer
    if metadata is None:
        client = getattr(instance, "_client", None)  # KafkaConsumer
        metadata = getattr(client, "cluster", None) if client else None
    return getattr(metadata, "_nr_cluster_id", None) if metadata else None


def _bind_update_metadata(metadata_response):
    return metadata_response


def wrap_ClusterMetadata_update_metadata(wrapped, instance, args, kwargs):
    try:
        metadata_response = _bind_update_metadata(*args, **kwargs)
        cluster_id = getattr(metadata_response, "cluster_id", None)
        if cluster_id:
            instance._nr_cluster_id = cluster_id
    except Exception:
        _logger.debug("NR Kafka cluster ID capture failed", exc_info=True)
    return wrapped(*args, **kwargs)


def _bind_send(topic, value=None, key=None, headers=None, partition=None, timestamp_ms=None):
    return topic, value, key, headers, partition, timestamp_ms


def wrap_KafkaProducer_send(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        topic, *_ = _bind_send(*args, **kwargs)
        topic = topic or "Default"
        cluster_id = _read_cluster_id(instance)
        if cluster_id:
            app = application_instance(activate=False)
            if app:
                app.record_custom_metric(KAFKA_CLUSTER_METRIC_PRODUCE.format(cluster_id, topic), 1)
        return wrapped(*args, **kwargs)

    topic, value, key, headers, partition, timestamp_ms = _bind_send(*args, **kwargs)
    topic = topic or "Default"
    headers = list(headers) if headers else []

    transaction.add_messagebroker_info(
        "Kafka-Python", get_package_version("kafka-python") or get_package_version("kafka-python-ng")
    )

    with MessageTrace(
        library="Kafka",
        operation="Produce",
        destination_type="Topic",
        destination_name=topic,
        source=wrapped,
        terminal=False,
    ):
        dt_headers = [(k, v.encode("utf-8")) for k, v in MessageTrace.generate_request_headers(transaction)]
        # headers can be a list of tuples or a dict so convert to dict for consistency.
        if headers:
            dt_headers.extend(headers)

        if hasattr(instance, "config"):
            for server_name in instance.config.get("bootstrap_servers", []):
                transaction.record_custom_metric(f"MessageBroker/Kafka/Nodes/{server_name}/Produce/{topic}", 1)

        cluster_id = _read_cluster_id(instance)
        if cluster_id:
            transaction.record_custom_metric(
                KAFKA_CLUSTER_METRIC_PRODUCE.format(cluster_id, topic), 1
            )

        try:
            return wrapped(
                topic, value=value, key=key, headers=dt_headers, partition=partition, timestamp_ms=timestamp_ms
            )
        except Exception:
            notice_error()
            raise


def wrap_kafkaconsumer_next(wrapped, instance, args, kwargs):
    if hasattr(instance, "_nr_transaction") and not instance._nr_transaction.stopped:
        instance._nr_transaction.__exit__(*sys.exc_info())

    try:
        record = wrapped(*args, **kwargs)
    except Exception as e:
        # StopIteration ends iteration normally — do not capture.
        if not isinstance(e, StopIteration):
            if current_transaction():
                notice_error()
            else:
                notice_error(application=application_instance(activate=False))
        raise

    if record:
        library = "Kafka"
        destination_type = "Topic"
        destination_name = record.topic
        received_bytes = len(str(record.value).encode("utf-8"))
        message_count = 1

        transaction = current_transaction(active_only=False)

        if not transaction:
            transaction = MessageTransaction(
                application=application_instance(),
                library=library,
                destination_type=destination_type,
                destination_name=destination_name,
                headers=dict(record.headers),
                transport_type="Kafka",
                routing_key=record.key,
                source=wrapped,
            )
            instance._nr_transaction = transaction
            transaction.__enter__()

            if hasattr(instance, "config") and "client_id" in instance.config:
                client_id = instance.config["client_id"]
                transaction._add_agent_attribute("kafka.consume.client_id", client_id)

            transaction._add_agent_attribute("kafka.consume.byteCount", received_bytes)

        transaction = current_transaction()
        if transaction:
            group = f"Message/{library}/{destination_type}"
            name = f"Named/{destination_name}"
            transaction.record_custom_metric(f"{group}/{name}/Received/Bytes", received_bytes)
            transaction.record_custom_metric(f"{group}/{name}/Received/Messages", message_count)
            if hasattr(instance, "config"):
                for server_name in instance.config.get("bootstrap_servers", []):
                    transaction.record_custom_metric(
                        f"MessageBroker/Kafka/Nodes/{server_name}/Consume/{destination_name}", 1
                    )

            cluster_id = _read_cluster_id(instance)
            if cluster_id:
                transaction.record_custom_metric(
                    KAFKA_CLUSTER_METRIC_CONSUME.format(cluster_id, destination_name), 1
                )
            transaction.add_messagebroker_info(
                "Kafka-Python", get_package_version("kafka-python") or get_package_version("kafka-python-ng")
            )

    return record


def wrap_KafkaProducer_init(wrapped, instance, args, kwargs):
    get_config_key = lambda key: kwargs.get(key, instance.DEFAULT_CONFIG[key])  # noqa: E731

    kwargs["key_serializer"] = wrap_serializer(
        instance, "Serialization/Key", "MessageBroker", get_config_key("key_serializer")
    )
    kwargs["value_serializer"] = wrap_serializer(
        instance, "Serialization/Value", "MessageBroker", get_config_key("value_serializer")
    )

    return wrapped(*args, **kwargs)


class NewRelicSerializerWrapper(ObjectProxy):
    def __init__(self, wrapped, serializer_name, group_prefix):
        ObjectProxy.__init__.__get__(self)(wrapped)

        self._nr_serializer_name = serializer_name
        self._nr_group_prefix = group_prefix

    def serialize(self, topic, object):  # noqa: A002
        wrapped = self.__wrapped__.serialize
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
            message_trace = current_trace()
            while message_trace is not None and not isinstance(message_trace, MessageTrace):
                message_trace = message_trace.parent
            if message_trace:
                topic = message_trace.destination_name

        group = f"{group_prefix}/Kafka/Topic"
        name = f"Named/{topic}/{serializer_name}"

        return FunctionTraceWrapper(wrapped, name=name, group=group)(*args, **kwargs)

    try:
        if serializer is None:
            return serializer
        elif isinstance(serializer, Serializer):
            return NewRelicSerializerWrapper(serializer, group_prefix=group_prefix, serializer_name=serializer_name)
        else:
            return _wrap_serializer(serializer)
    except Exception:
        return serializer


def metric_wrapper(metric_name, check_result=False):
    def _metric_wrapper(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        application = application_instance(activate=False)
        if application:
            if not check_result or (check_result and result):
                application.record_custom_metric(metric_name, 1)

        return result

    return _metric_wrapper


def instrument_kafka_cluster(module):
    if hasattr(module, "ClusterMetadata") and hasattr(module.ClusterMetadata, "update_metadata"):
        wrap_function_wrapper(module, "ClusterMetadata.update_metadata", wrap_ClusterMetadata_update_metadata)


def instrument_kafka_producer(module):
    if hasattr(module, "KafkaProducer"):
        wrap_function_wrapper(module, "KafkaProducer.__init__", wrap_KafkaProducer_init)
        wrap_function_wrapper(module, "KafkaProducer.send", wrap_KafkaProducer_send)


def instrument_kafka_consumer_group(module):
    if hasattr(module, "KafkaConsumer"):
        wrap_function_wrapper(module, "KafkaConsumer.__next__", wrap_kafkaconsumer_next)


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
