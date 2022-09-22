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


def test_data_source_metrics(data_source, topic, get_consumer_records):
    _data_source_metrics = {
        "MessageBroker/Kafka/Internal/kafka-metrics-count/count": "present",
        "MessageBroker/Kafka/Internal/producer-metrics/request-rate": "present",
        "MessageBroker/Kafka/Internal/producer-topic-metrics.%s/record-send-rate" % topic: "present",
        "MessageBroker/Kafka/Internal/consumer-metrics/request-rate": "present",
    }

    get_consumer_records()

    metrics = dict(data_source())
    assert metrics

    for metric_name, count in six.iteritems(_data_source_metrics):
        if count == "present":
            assert metric_name in metrics
        else:
            assert metrics[metric_name]["count"] == count, "%s:%d" % (metric_name, count)
