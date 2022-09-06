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

from newrelic.packages import six


def test_data_source_metrics(data_source, topic, producer, consumer):
    _data_source_metrics = {
        "MessageBroker/Kafka/Internal/kafka-metrics-count/count": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/connection-close-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/connection-creation-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/select-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/io-wait-time-ns-avg": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/io-wait-ratio": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/io-time-ns-avg": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/io-ratio": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/connection-count": 1,
        "MessageBroker/Kafka/Internal/producer-metrics/batch-size-avg": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/batch-size-max": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/compression-rate-avg": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/record-queue-time-avg": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/record-queue-time-max": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/record-send-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/records-per-request-avg": 1,
        "MessageBroker/Kafka/Internal/producer-metrics/byte-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/record-size-max": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/record-size-avg": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/metadata-age": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/network-io-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/outgoing-byte-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/request-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/request-size-avg": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/request-size-max": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/incoming-byte-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/response-rate": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/request-latency-avg": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/request-latency-max": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/outgoing-byte-rate": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-rate": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-size-avg": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-size-max": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/incoming-byte-rate": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/response-rate": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-latency-avg": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-latency-max": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/outgoing-byte-rate": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-rate": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-size-avg": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-size-max": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/incoming-byte-rate": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/response-rate": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-latency-avg": "present",
        "MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-latency-max": "present",
        "MessageBroker/Kafka/Internal/producer-topic-metrics.%s/record-send-rate" % topic: "present",
        "MessageBroker/Kafka/Internal/producer-topic-metrics.%s/byte-rate" % topic: "present",
        "MessageBroker/Kafka/Internal/producer-topic-metrics.%s/compression-rate" % topic: "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/connection-close-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/connection-creation-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/select-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/io-wait-time-ns-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/io-wait-ratio": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/io-time-ns-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/io-ratio": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/connection-count": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/network-io-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/outgoing-byte-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/request-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/request-size-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/request-size-max": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/incoming-byte-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/response-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/request-latency-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/request-latency-max": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/outgoing-byte-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-size-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-size-max": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/incoming-byte-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/response-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-latency-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-latency-max": "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-size-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-size-max": "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/bytes-consumed-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/records-per-request-avg": 1,
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/records-consumed-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-latency-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-latency-max": "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/records-lag-max": "present",
        "MessageBroker/Kafka/Internal/consumer-coordinator-metrics/assigned-partitions": 1,
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/outgoing-byte-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-size-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-size-max": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/incoming-byte-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/response-rate": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-latency-avg": "present",
        "MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-latency-max": "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/%s/fetch-size-avg" % topic: "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/%s/fetch-size-max" % topic: "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/%s/bytes-consumed-rate" % topic: "present",
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/%s/records-per-request-avg" % topic: 1,
        "MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/%s/records-consumed-rate" % topic: "present",
    }

    producer.send(topic, value=1)
    producer.flush()
    next(iter(consumer))

    metrics = dict(data_source())
    assert metrics

    for metric_name, count in six.iteritems(_data_source_metrics):
        if count == "present":
            assert metric_name in metrics
        else:
            assert metrics[metric_name]["count"] == count, "%s:%d" % (metric_name, count)
