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
import threading

from kafka.metrics.metrics_reporter import AbstractMetricsReporter

import newrelic.core.agent
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.packages import six
from newrelic.samplers.decorators import data_source_factory

_logger = logging.getLogger(__name__)


class KafkaMetricsDataSource(object):
    _instance = None

    def __init__(self):
        self.reporters = []

    @data_source_factory(name="Kafka Metrics Reporter")
    @classmethod
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
        super(NewRelicMetricsReporter).__init__(*args, **kwargs)

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


def instrument_kafka_consumer_group(module):
    if hasattr(module, "KafkaConsumer"):
        wrap_function_wrapper(module, "KafkaConsumer.__init__", wrap_KafkaProducerConsumer_init)
