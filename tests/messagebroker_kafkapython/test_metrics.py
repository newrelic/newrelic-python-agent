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


def test_data_source_metrics(data_source, topic, producer, consumer):
    producer.send(topic, value=1)
    producer.flush()
    next(iter(consumer))

    metrics = dict(data_source())
    metric_names = list(metrics.keys())
    assert metrics


# Example metrics

# MessageBroker/Kafka/Internal/kafka-metrics-count/count
# MessageBroker/Kafka/Internal/producer-metrics/connection-close-rate
# MessageBroker/Kafka/Internal/producer-metrics/connection-creation-rate
# MessageBroker/Kafka/Internal/producer-metrics/select-rate
# MessageBroker/Kafka/Internal/producer-metrics/io-wait-time-ns-avg
# MessageBroker/Kafka/Internal/producer-metrics/io-wait-ratio
# MessageBroker/Kafka/Internal/producer-metrics/io-time-ns-avg
# MessageBroker/Kafka/Internal/producer-metrics/io-ratio
# MessageBroker/Kafka/Internal/producer-metrics/connection-count
# MessageBroker/Kafka/Internal/producer-metrics/batch-size-avg
# MessageBroker/Kafka/Internal/producer-metrics/batch-size-max
# MessageBroker/Kafka/Internal/producer-metrics/compression-rate-avg
# MessageBroker/Kafka/Internal/producer-metrics/record-queue-time-avg
# MessageBroker/Kafka/Internal/producer-metrics/record-queue-time-max
# MessageBroker/Kafka/Internal/producer-metrics/record-send-rate
# MessageBroker/Kafka/Internal/producer-metrics/records-per-request-avg
# MessageBroker/Kafka/Internal/producer-metrics/byte-rate
# MessageBroker/Kafka/Internal/producer-metrics/record-size-max
# MessageBroker/Kafka/Internal/producer-metrics/record-size-avg
# MessageBroker/Kafka/Internal/producer-metrics/metadata-age
# MessageBroker/Kafka/Internal/producer-metrics/network-io-rate
# MessageBroker/Kafka/Internal/producer-metrics/outgoing-byte-rate
# MessageBroker/Kafka/Internal/producer-metrics/request-rate
# MessageBroker/Kafka/Internal/producer-metrics/request-size-avg
# MessageBroker/Kafka/Internal/producer-metrics/request-size-max
# MessageBroker/Kafka/Internal/producer-metrics/incoming-byte-rate
# MessageBroker/Kafka/Internal/producer-metrics/response-rate
# MessageBroker/Kafka/Internal/producer-metrics/request-latency-avg
# MessageBroker/Kafka/Internal/producer-metrics/request-latency-max
# MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/outgoing-byte-rate
# MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-rate
# MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-size-avg
# MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-size-max
# MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/incoming-byte-rate
# MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/response-rate
# MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-latency-avg
# MessageBroker/Kafka/Internal/producer-node-metrics.node-bootstrap-0/request-latency-max
# MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/outgoing-byte-rate
# MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-rate
# MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-size-avg
# MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-size-max
# MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/incoming-byte-rate
# MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/response-rate
# MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-latency-avg
# MessageBroker/Kafka/Internal/producer-node-metrics.node-1001/request-latency-max
# MessageBroker/Kafka/Internal/producer-topic-metrics.test-topic-c962647a-f6cf-4a24-a90b-40ab2364dc55/record-send-rate
# MessageBroker/Kafka/Internal/producer-topic-metrics.test-topic-c962647a-f6cf-4a24-a90b-40ab2364dc55/byte-rate
# MessageBroker/Kafka/Internal/producer-topic-metrics.test-topic-c962647a-f6cf-4a24-a90b-40ab2364dc55/compression-rate
# MessageBroker/Kafka/Internal/consumer-metrics/connection-close-rate
# MessageBroker/Kafka/Internal/consumer-metrics/connection-creation-rate
# MessageBroker/Kafka/Internal/consumer-metrics/select-rate
# MessageBroker/Kafka/Internal/consumer-metrics/io-wait-time-ns-avg
# MessageBroker/Kafka/Internal/consumer-metrics/io-wait-ratio
# MessageBroker/Kafka/Internal/consumer-metrics/io-time-ns-avg
# MessageBroker/Kafka/Internal/consumer-metrics/io-ratio
# MessageBroker/Kafka/Internal/consumer-metrics/connection-count
# MessageBroker/Kafka/Internal/consumer-metrics/network-io-rate
# MessageBroker/Kafka/Internal/consumer-metrics/outgoing-byte-rate
# MessageBroker/Kafka/Internal/consumer-metrics/request-rate
# MessageBroker/Kafka/Internal/consumer-metrics/request-size-avg
# MessageBroker/Kafka/Internal/consumer-metrics/request-size-max
# MessageBroker/Kafka/Internal/consumer-metrics/incoming-byte-rate
# MessageBroker/Kafka/Internal/consumer-metrics/response-rate
# MessageBroker/Kafka/Internal/consumer-metrics/request-latency-avg
# MessageBroker/Kafka/Internal/consumer-metrics/request-latency-max
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/outgoing-byte-rate
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-rate
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-size-avg
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-size-max
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/incoming-byte-rate
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/response-rate
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-latency-avg
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-bootstrap-0/request-latency-max
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-size-avg
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-size-max
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/bytes-consumed-rate
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/records-per-request-avg
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/records-consumed-rate
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-latency-avg
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-latency-max
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/fetch-rate
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/records-lag-max
# MessageBroker/Kafka/Internal/consumer-coordinator-metrics/assigned-partitions
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/outgoing-byte-rate
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-rate
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-size-avg
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-size-max
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/incoming-byte-rate
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/response-rate
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-latency-avg
# MessageBroker/Kafka/Internal/consumer-node-metrics.node-1001/request-latency-max
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/test-topic-c962647a-f6cf-4a24-a90b-40ab2364dc55/fetch-size-avg
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/test-topic-c962647a-f6cf-4a24-a90b-40ab2364dc55/fetch-size-max
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/test-topic-c962647a-f6cf-4a24-a90b-40ab2364dc55/bytes-consumed-rate
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/test-topic-c962647a-f6cf-4a24-a90b-40ab2364dc55/records-per-request-avg
# MessageBroker/Kafka/Internal/consumer-fetch-manager-metrics/test-topic-c962647a-f6cf-4a24-a90b-40ab2364dc55/records-consumed-rate
