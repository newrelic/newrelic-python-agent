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
import threading

from kafka.serializer import Serializer

from newrelic.api.application import application_instance
from newrelic.api.function_trace import FunctionTraceWrapper
from newrelic.api.message_trace import MessageTrace
from newrelic.api.message_transaction import MessageTransaction
from newrelic.api.time_trace import current_trace, notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy, function_wrapper, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version

HEARTBEAT_POLL = "MessageBroker/Kafka/Heartbeat/Poll"
HEARTBEAT_SENT = "MessageBroker/Kafka/Heartbeat/Sent"
HEARTBEAT_FAIL = "MessageBroker/Kafka/Heartbeat/Fail"
HEARTBEAT_RECEIVE = "MessageBroker/Kafka/Heartbeat/Receive"
HEARTBEAT_SESSION_TIMEOUT = "MessageBroker/Kafka/Heartbeat/SessionTimeout"
HEARTBEAT_POLL_TIMEOUT = "MessageBroker/Kafka/Heartbeat/PollTimeout"

KAFKA_CLUSTER_METRIC_PRODUCE = "MessageBroker/Kafka/Cluster/{0}/Topic/{1}/Produce"
KAFKA_CLUSTER_METRIC_CONSUME = "MessageBroker/Kafka/Cluster/{0}/Topic/{1}/Consume"

_kafka_cluster_id_cache = {}
_nr_cluster_id_cache_lock = threading.Lock()
_logger = logging.getLogger(__name__)


def _bootstrap_cache_key(bootstrap_servers):
    """Normalize bootstrap_servers (str or iterable) to the cluster-ID cache key."""
    if isinstance(bootstrap_servers, str):
        bootstrap_servers = [bootstrap_servers]
    return ",".join(sorted(str(s) for s in bootstrap_servers))


def _bind_send(topic, value=None, key=None, headers=None, partition=None, timestamp_ms=None):
    return topic, value, key, headers, partition, timestamp_ms


def wrap_KafkaProducer_send(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
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

        servers = instance.config.get("bootstrap_servers", []) if hasattr(instance, "config") else []
        cluster_id = None
        if servers:
            _cache_key = _bootstrap_cache_key(servers)
            cluster_id = _kafka_cluster_id_cache.get(_cache_key) or None
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

            servers = instance.config.get("bootstrap_servers", []) if hasattr(instance, "config") else []
            cluster_id = None
            if servers:
                _cache_key = _bootstrap_cache_key(servers)
                cached = _kafka_cluster_id_cache.get(_cache_key)
                cluster_id = cached if cached else None
            if cluster_id:
                transaction.record_custom_metric(
                    KAFKA_CLUSTER_METRIC_CONSUME.format(cluster_id, destination_name), 1
                )
            transaction.add_messagebroker_info(
                "Kafka-Python", get_package_version("kafka-python") or get_package_version("kafka-python-ng")
            )

    return record


_SECURITY_CONFIG_KEYS = (
    "security_protocol", "ssl_context", "ssl_cafile", "ssl_certfile",
    "ssl_keyfile", "ssl_password", "ssl_crlfile", "ssl_ciphers",
    "sasl_mechanism", "sasl_plain_username", "sasl_plain_password",
    "sasl_kerberos_service_name", "sasl_kerberos_domain_name",
    "sasl_oauth_token_provider",
)


def _fetch_cluster_id_kafka_python(bootstrap_servers, instance_config=None):
    cache_key = _bootstrap_cache_key(bootstrap_servers)
    with _nr_cluster_id_cache_lock:
        if _kafka_cluster_id_cache.get(cache_key) is not None:
            return
        _kafka_cluster_id_cache[cache_key] = ""  # sentinel to prevent duplicate fetches

    try:
        from kafka.admin import KafkaAdminClient as _KafkaAdminClient
        if not hasattr(_KafkaAdminClient, "describe_cluster"):
            return
    except ImportError:
        return

    def _run():
        admin = None
        cluster_id = None
        try:
            from kafka.admin import KafkaAdminClient
            extra = {k: instance_config[k] for k in _SECURITY_CONFIG_KEYS if instance_config and k in instance_config and instance_config[k] is not None}
            admin = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                client_id="newrelic-cluster-id-probe",
                api_version_auto_timeout_ms=5000,
                **extra,
            )
            meta = admin._client.cluster
            admin._client.poll(timeout_ms=3000)
            try:
                result = admin.describe_cluster()
                cluster_id = getattr(result, "cluster_id", None) or getattr(result, "clusterId", None)
            except Exception:
                _logger.debug("NR Kafka describe_cluster failed", exc_info=True)
            if not cluster_id:
                cluster_id = getattr(meta, "cluster_id", None) or getattr(meta, "_cluster_id", None)
        except Exception:
            _logger.debug("NR Kafka cluster ID fetch failed", exc_info=True)
        finally:
            try:
                if admin is not None:
                    admin.close()
            except Exception:
                pass
        if cluster_id:
            with _nr_cluster_id_cache_lock:
                _kafka_cluster_id_cache[cache_key] = cluster_id
        else:
            with _nr_cluster_id_cache_lock:
                _kafka_cluster_id_cache.pop(cache_key, None)

    threading.Thread(target=_run, daemon=True, name="NR-KafkaPython-ClusterId").start()


def wrap_KafkaProducer_init(wrapped, instance, args, kwargs):
    get_config_key = lambda key: kwargs.get(key, instance.DEFAULT_CONFIG[key])  # noqa: E731

    kwargs["key_serializer"] = wrap_serializer(
        instance, "Serialization/Key", "MessageBroker", get_config_key("key_serializer")
    )
    kwargs["value_serializer"] = wrap_serializer(
        instance, "Serialization/Value", "MessageBroker", get_config_key("value_serializer")
    )

    result = wrapped(*args, **kwargs)

    servers = instance.config.get("bootstrap_servers", [])
    if servers:
        _fetch_cluster_id_kafka_python(servers, instance.config)

    return result


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


def instrument_kafka_producer(module):
    if hasattr(module, "KafkaProducer"):
        wrap_function_wrapper(module, "KafkaProducer.__init__", wrap_KafkaProducer_init)
        wrap_function_wrapper(module, "KafkaProducer.send", wrap_KafkaProducer_send)


def _wrap_KafkaConsumer_init(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    servers = instance.config.get("bootstrap_servers", [])
    if servers:
        _fetch_cluster_id_kafka_python(servers, instance.config)
    return result


def instrument_kafka_consumer_group(module):
    if hasattr(module, "KafkaConsumer"):
        wrap_function_wrapper(module, "KafkaConsumer.__init__", _wrap_KafkaConsumer_init)
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
