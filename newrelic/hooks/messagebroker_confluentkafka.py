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
import time
import weakref

from newrelic.api.application import application_instance
from newrelic.api.error_trace import wrap_error_trace
from newrelic.api.function_trace import FunctionTraceWrapper
from newrelic.api.message_trace import MessageTrace
from newrelic.api.message_transaction import MessageTransaction
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)

HEARTBEAT_POLL = "MessageBroker/Kafka/Heartbeat/Poll"
HEARTBEAT_SENT = "MessageBroker/Kafka/Heartbeat/Sent"
HEARTBEAT_FAIL = "MessageBroker/Kafka/Heartbeat/Fail"
HEARTBEAT_RECEIVE = "MessageBroker/Kafka/Heartbeat/Receive"
HEARTBEAT_SESSION_TIMEOUT = "MessageBroker/Kafka/Heartbeat/SessionTimeout"
HEARTBEAT_POLL_TIMEOUT = "MessageBroker/Kafka/Heartbeat/PollTimeout"

KAFKA_CLUSTER_METRIC_PRODUCE = "MessageBroker/Kafka/Cluster/{0}/Topic/{1}/Produce"
KAFKA_CLUSTER_METRIC_CONSUME = "MessageBroker/Kafka/Cluster/{0}/Topic/{1}/Consume"


_CLUSTER_ID_TTL_SECONDS = 60 * 60

_nr_cluster_id_cache = {}
_nr_cluster_id_cache_lock = threading.Lock()


def _fetch_cluster_id(instance):
    settings = global_settings()
    if not getattr(getattr(settings, "kafka", None), "cluster_metrics_enabled", False):
        return
    servers = getattr(instance, "_nr_bootstrap_servers", None)
    # Sort so that equivalent broker sets with different orderings share the same key.
    cache_key = ",".join(sorted(servers)) if servers else None

    if cache_key:
        with _nr_cluster_id_cache_lock:
            cached = _nr_cluster_id_cache.get(cache_key)
            if isinstance(cached, tuple):
                cluster_id, ts = cached
                if time.monotonic() - ts <= _CLUSTER_ID_TTL_SECONDS:
                    instance._nr_cluster_id = cluster_id
                    instance._nr_cluster_id_fetched_at = ts
                    return
                # Expired — fall through to start a new fetch.
            elif cached is not None:
                # "" sentinel — fetch already in progress.
                return
            _nr_cluster_id_cache[cache_key] = ""

    # Hold only a weak reference so the thread closure does not extend the
    # lifetime of a Producer/Consumer that the caller has already abandoned.
    instance_ref = weakref.ref(instance)

    def _run():
        inst = instance_ref()
        if inst is None:
            # Instance was GC'd before the thread ran; clean up sentinel and exit.
            if cache_key:
                with _nr_cluster_id_cache_lock:
                    _nr_cluster_id_cache.pop(cache_key, None)
            return
        try:
            meta = inst.list_topics(timeout=5)
            cluster_id = getattr(meta, "cluster_id", None)
            if cluster_id:
                now = time.monotonic()
                inst._nr_cluster_id = cluster_id
                inst._nr_cluster_id_fetched_at = now
                if cache_key:
                    with _nr_cluster_id_cache_lock:
                        _nr_cluster_id_cache[cache_key] = (cluster_id, now)
        except Exception:
            _logger.debug("NR Kafka cluster ID fetch failed", exc_info=True)
            if cache_key:
                with _nr_cluster_id_cache_lock:
                    _nr_cluster_id_cache.pop(cache_key, None)

    threading.Thread(target=_run, daemon=True, name="NR-Kafka-ClusterId").start()


def wrap_Producer_produce(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction is None:
        return wrapped(*args, **kwargs)

    # Binding with a standard function signature does not work properly due to a bug in handling arguments
    # in the underlying C code, where callback=None being specified causes on_delivery=callback to never run.

    # Bind out headers from end of args list
    if len(args) == 8:
        # Take headers off the end of the positional args
        headers = args[7]
        args = args[0:7]
    else:
        headers = kwargs.pop("headers", [])

    # Bind topic off of the beginning of the args list
    if len(args) >= 1:
        topic = args[0]
        args = args[1:]
    else:
        topic = kwargs.pop("topic", None)
    topic = topic or "Default"

    transaction.add_messagebroker_info("Confluent-Kafka", get_package_version("confluent-kafka"))
    if hasattr(instance, "_nr_bootstrap_servers"):
        for server_name in instance._nr_bootstrap_servers:
            transaction.record_custom_metric(f"MessageBroker/Kafka/Nodes/{server_name}/Produce/{topic}", 1)

    cluster_id = getattr(instance, "_nr_cluster_id", None)
    if cluster_id:
        if time.monotonic() - getattr(instance, "_nr_cluster_id_fetched_at", 0.0) > _CLUSTER_ID_TTL_SECONDS:
            _fetch_cluster_id(instance)  # background re-fetch; use stale value below
    elif hasattr(instance, "_nr_bootstrap_servers"):
        _cache_key = ",".join(sorted(instance._nr_bootstrap_servers))
        _cached = _nr_cluster_id_cache.get(_cache_key)
        if isinstance(_cached, tuple):
            cluster_id, _ts = _cached
            instance._nr_cluster_id = cluster_id
            instance._nr_cluster_id_fetched_at = _ts
            if time.monotonic() - _ts > _CLUSTER_ID_TTL_SECONDS:
                _fetch_cluster_id(instance)  # background re-fetch
    if cluster_id:
        transaction.record_custom_metric(
            KAFKA_CLUSTER_METRIC_PRODUCE.format(cluster_id, topic), 1
        )

    with MessageTrace(
        library="Kafka", operation="Produce", destination_type="Topic", destination_name=topic, source=wrapped
    ):
        dt_headers = {k: v.encode("utf-8") for k, v in MessageTrace.generate_request_headers(transaction)}
        # headers can be a list of tuples or a dict so convert to dict for consistency.
        if headers:
            dt_headers.update(dict(headers))

        try:
            return wrapped(topic, *args, **kwargs, headers=dt_headers)
        except Exception as error:
            # Unwrap kafka errors
            while hasattr(error, "exception"):
                error = error.exception

            _, _, tb = sys.exc_info()
            notice_error((type(error), error, tb))
            tb = None  # Clear reference to prevent reference cycles
            raise


def wrap_Consumer_poll(wrapped, instance, args, kwargs):
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

    # Step 1: Stop existing transactions
    if hasattr(instance, "_nr_transaction") and not instance._nr_transaction.stopped:
        instance._nr_transaction.__exit__(*sys.exc_info())

    # Step 2: Poll for records
    try:
        record = wrapped(*args, **kwargs)
    except Exception:
        if current_transaction():
            notice_error()
        else:
            notice_error(application=application_instance(activate=False))
        raise

    # Step 3: Start new transaction for received record
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
            group = f"Message/{library}/{destination_type}"
            name = f"Named/{destination_name}"
            transaction.record_custom_metric(f"{group}/{name}/Received/Bytes", received_bytes)
            transaction.record_custom_metric(f"{group}/{name}/Received/Messages", message_count)
            if hasattr(instance, "_nr_bootstrap_servers"):
                for server_name in instance._nr_bootstrap_servers:
                    transaction.record_custom_metric(
                        f"MessageBroker/Kafka/Nodes/{server_name}/Consume/{destination_name}", 1
                    )
            cluster_id = getattr(instance, "_nr_cluster_id", None)
            if cluster_id:
                if time.monotonic() - getattr(instance, "_nr_cluster_id_fetched_at", 0.0) > _CLUSTER_ID_TTL_SECONDS:
                    _fetch_cluster_id(instance)  # background re-fetch; use stale value below
            elif hasattr(instance, "_nr_bootstrap_servers"):
                _cache_key = ",".join(sorted(instance._nr_bootstrap_servers))
                _cached = _nr_cluster_id_cache.get(_cache_key)
                if isinstance(_cached, tuple):
                    cluster_id, _ts = _cached
                    instance._nr_cluster_id = cluster_id
                    instance._nr_cluster_id_fetched_at = _ts
                    if time.monotonic() - _ts > _CLUSTER_ID_TTL_SECONDS:
                        _fetch_cluster_id(instance)  # background re-fetch
            if cluster_id:
                transaction.record_custom_metric(
                    KAFKA_CLUSTER_METRIC_CONSUME.format(cluster_id, destination_name), 1
                )
            transaction.add_messagebroker_info("Confluent-Kafka", get_package_version("confluent-kafka"))

    return record


def wrap_DeserializingConsumer_poll(wrapped, instance, args, kwargs):
    try:
        return wrapped(*args, **kwargs)
    except Exception:
        notice_error()

        # Stop existing transactions
        if hasattr(instance, "_nr_transaction") and not instance._nr_transaction.stopped:
            instance._nr_transaction.__exit__(*sys.exc_info())

        raise


def wrap_serializer(serializer_name, group_prefix):
    @function_wrapper
    def _wrap_serializer(wrapped, instance, args, kwargs):
        if not current_transaction():
            return wrapped(*args, **kwargs)

        topic = args[1].topic
        group = f"{group_prefix}/Kafka/Topic"
        name = f"Named/{topic}/{serializer_name}"

        return FunctionTraceWrapper(wrapped, name=name, group=group)(*args, **kwargs)

    return _wrap_serializer


def wrap_SerializingProducer_init(wrapped, instance, args, kwargs):
    wrapped(*args, **kwargs)

    if hasattr(instance, "_key_serializer") and callable(instance._key_serializer):
        instance._key_serializer = wrap_serializer("Serialization/Key", "MessageBroker")(instance._key_serializer)

    if hasattr(instance, "_value_serializer") and callable(instance._value_serializer):
        instance._value_serializer = wrap_serializer("Serialization/Value", "MessageBroker")(instance._value_serializer)

    try:
        conf = kwargs.get("conf") or (args[0] if args else {})
        servers = conf.get("bootstrap.servers") if isinstance(conf, dict) else None
        if servers:
            instance._nr_bootstrap_servers = servers.split(",")
    except Exception:
        pass

    _fetch_cluster_id(instance)


def wrap_DeserializingConsumer_init(wrapped, instance, args, kwargs):
    wrapped(*args, **kwargs)

    if hasattr(instance, "_key_deserializer") and callable(instance._key_deserializer):
        instance._key_deserializer = wrap_serializer("Deserialization/Key", "Message")(instance._key_deserializer)

    if hasattr(instance, "_value_deserializer") and callable(instance._value_deserializer):
        instance._value_deserializer = wrap_serializer("Deserialization/Value", "Message")(instance._value_deserializer)

    try:
        conf = kwargs.get("conf") or (args[0] if args else {})
        servers = conf.get("bootstrap.servers") if isinstance(conf, dict) else None
        if servers:
            instance._nr_bootstrap_servers = servers.split(",")
    except Exception:
        pass

    _fetch_cluster_id(instance)


def wrap_Producer_init(wrapped, instance, args, kwargs):
    wrapped(*args, **kwargs)

    # Try to capture the boostrap server info that is passed in in the configuration.
    try:
        conf = args[0]
        servers = conf.get("bootstrap.servers")
        if servers:
            instance._nr_bootstrap_servers = servers.split(",")
    except Exception:
        pass

    _fetch_cluster_id(instance)


def wrap_Consumer_init(wrapped, instance, args, kwargs):
    wrapped(*args, **kwargs)

    # Try to capture the boostrap server info that is passed in in the configuration.
    try:
        conf = args[0]
        servers = conf.get("bootstrap.servers")
        if servers:
            instance._nr_bootstrap_servers = servers.split(",")
    except Exception:
        pass

    _fetch_cluster_id(instance)


def wrap_immutable_class(module, class_name):
    # Wrap immutable binary extension class with a mutable Python subclass
    new_class = type(class_name, (getattr(module, class_name),), {})
    setattr(module, class_name, new_class)
    return new_class


def instrument_confluentkafka_cimpl(module):
    if hasattr(module, "Producer"):
        wrap_immutable_class(module, "Producer")
        wrap_function_wrapper(module, "Producer.produce", wrap_Producer_produce)
        wrap_function_wrapper(module, "Producer.__init__", wrap_Producer_init)

    if hasattr(module, "Consumer"):
        wrap_immutable_class(module, "Consumer")
        wrap_function_wrapper(module, "Consumer.poll", wrap_Consumer_poll)
        wrap_function_wrapper(module, "Consumer.__init__", wrap_Consumer_init)


def instrument_confluentkafka_serializing_producer(module):
    if hasattr(module, "SerializingProducer"):
        wrap_function_wrapper(module, "SerializingProducer.__init__", wrap_SerializingProducer_init)
        wrap_error_trace(module, "SerializingProducer.produce")


def instrument_confluentkafka_deserializing_consumer(module):
    if hasattr(module, "DeserializingConsumer"):
        wrap_function_wrapper(module, "DeserializingConsumer.__init__", wrap_DeserializingConsumer_init)
        wrap_function_wrapper(module, "DeserializingConsumer.poll", wrap_DeserializingConsumer_poll)
