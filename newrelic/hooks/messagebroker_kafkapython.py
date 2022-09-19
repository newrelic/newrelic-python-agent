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
import math
import sys
import threading

from kafka.metrics.metrics_reporter import AbstractMetricsReporter

import newrelic.core.agent
from newrelic.api.application import application_instance
from newrelic.api.message_trace import MessageTrace
from newrelic.api.message_transaction import MessageTransaction
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.packages import six
from newrelic.samplers.decorators import data_source_factory

_logger = logging.getLogger(__name__)

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


def wrap_kafkaconsumer_next(wrapped, instance, args, kwargs):
    if hasattr(instance, "_nr_transaction") and not instance._nr_transaction.stopped:
        instance._nr_transaction.__exit__(*sys.exc_info())

    try:
        record = wrapped(*args, **kwargs)
    except Exception as e:
        # StopIteration is an expected error, indicating the end of an iterable,
        # that should not be captured.
        if not isinstance(e, StopIteration):
            notice_error()
        raise

    if record:
        # This iterator can be called either outside of a transaction, or
        # within the context of an existing transaction.  There are 3
        # possibilities we need to handle: (Note that this is similar to
        # our Pika and Celery instrumentation)
        #
        #   1. In an inactive transaction
        #
        #      If the end_of_transaction() or ignore_transaction() API
        #      calls have been invoked, this iterator may be called in the
        #      context of an inactive transaction. In this case, don't wrap
        #      the iterator in any way. Just run the original iterator.
        #
        #   2. In an active transaction
        #
        #      Do nothing.
        #
        #   3. Outside of a transaction
        #
        #      Since it's not running inside of an existing transaction, we
        #      want to create a new background transaction for it.

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

            # Obtain consumer client_id to send up as agent attribute
            if hasattr(instance, "config") and "client_id" in instance.config:
                client_id = instance.config["client_id"]
                transaction._add_agent_attribute("kafka.consume.client_id", client_id)

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

    return record


class KafkaMetricsDataSource(object):
    _instance = None

    def __init__(self):
        self.reporters = []

    @classmethod
    @data_source_factory(name="Kafka Metrics Reporter")
    def factory(cls, settings=None, environ=None):
        return cls.singleton()

    @classmethod
    def singleton(cls, register=True):
        # If already initialized, exit early
        if cls._instance:
            return cls._instance

        # Init and register instance on class
        instance = cls()
        cls._instance = instance

        # register_data_source takes a callable so let it rerun singleton to retrieve the instance
        if register:
            try:
                _logger.debug("Registering kafka metrics data source.")
                newrelic.core.agent.agent_instance().register_data_source(cls.factory)
            except Exception:
                _logger.exception(
                    "Attempt to register kafka metrics data source has failed. Data source will be skipped."
                )

        return instance

    def register(self, reporter):
        self.reporters.append(reporter)

    def unregister(self, reporter):
        if reporter in self.reporters:
            self.reporters.remove(reporter)

    def start(self):
        return

    def stop(self):
        # Clear references to reporters to prevent them from participating in a reference cycle.
        self.reporters = []

    def __call__(self):
        for reporter in self.reporters:
            for name, metric in six.iteritems(reporter.snapshot()):
                yield name, metric


class NewRelicMetricsReporter(AbstractMetricsReporter):
    def __init__(self, *args, **kwargs):
        super(NewRelicMetricsReporter, self).__init__(*args, **kwargs)

        # Register with data source for harvesting
        self.data_source = KafkaMetricsDataSource.singleton()
        self.data_source.register(self)

        self._metrics = {}
        self._lock = threading.Lock()

    def close(self, *args, **kwargs):
        self.data_source.unregister(self)
        with self._lock:
            self._metrics = {}

    def init(self, metrics):
        for metric in metrics:
            self.metric_change(metric)

    @staticmethod
    def invalid_metric_value(metric):
        name, value = metric
        return not any((math.isinf(value), math.isnan(value), value == 0))

    def snapshot(self):
        with self._lock:
            # metric.value can only be called once, so care must be taken when filtering
            metrics = ((name, metric.value()) for name, metric in six.iteritems(self._metrics))
            return {
                "MessageBroker/Kafka/Internal/%s" % name: {"count": value}
                for name, value in filter(self.invalid_metric_value, metrics)
            }

    def get_metric_name(self, metric):
        metric_name = metric.metric_name  # Get MetricName object to work with

        name = metric_name.name
        group = metric_name.group

        if "topic" in metric_name.tags:
            topic = metric_name.tags["topic"]
            return "/".join((group, topic, name))
        else:
            return "/".join((group, name))

    def metric_change(self, metric):
        name = self.get_metric_name(metric)
        with self._lock:
            self._metrics[name] = metric

    def metric_removal(self, metric):
        name = self.get_metric_name(metric)
        with self._lock:
            if name in self._metrics:
                self._metrics.pop(name)

    def configure(self, configs):
        return


def wrap_KafkaProducerConsumer_init(wrapped, instance, args, kwargs):
    try:
        if "metric_reporters" in kwargs:
            metric_reporters = list(kwargs.get("metric_reporters", []))
            metric_reporters.append(NewRelicMetricsReporter)
            kwargs["metric_reporters"] = [metric_reporters]
        else:
            kwargs["metric_reporters"] = [NewRelicMetricsReporter]
    except Exception:
        pass

    return wrapped(*args, **kwargs)


def instrument_kafka_producer(module):
    if hasattr(module, "KafkaProducer"):
        wrap_function_wrapper(module, "KafkaProducer.__init__", wrap_KafkaProducerConsumer_init)
        wrap_function_wrapper(module, "KafkaProducer.send", wrap_KafkaProducer_send)


def instrument_kafka_consumer_group(module):
    if hasattr(module, "KafkaConsumer"):
        wrap_function_wrapper(module, "KafkaConsumer.__init__", wrap_KafkaProducerConsumer_init)
        wrap_function_wrapper(module.KafkaConsumer, "__next__", wrap_kafkaconsumer_next)
