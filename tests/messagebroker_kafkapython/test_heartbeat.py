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

import time

import kafka
from testing_support.validators.validate_custom_metrics_outside_transaction import (
    validate_custom_metrics_outside_transaction,
)


@validate_custom_metrics_outside_transaction(
    [
        ("MessageBroker/Kafka/Heartbeat/Poll", "present"),
        ("MessageBroker/Kafka/Heartbeat/Sent", "present"),
        ("MessageBroker/Kafka/Heartbeat/Receive", "present"),
        ("MessageBroker/Kafka/Heartbeat/Fail", None),
        ("MessageBroker/Kafka/Heartbeat/SessionTimeout", None),
        ("MessageBroker/Kafka/Heartbeat/PollTimeout", None),
    ]
)
def test_successful_heartbeat_metrics_recorded(topic, get_consumer_record):
    get_consumer_record()
    time.sleep(1.5)


@validate_custom_metrics_outside_transaction(
    [
        ("MessageBroker/Kafka/Heartbeat/Poll", "present"),
        ("MessageBroker/Kafka/Heartbeat/Sent", "present"),
        ("MessageBroker/Kafka/Heartbeat/Fail", "present"),
        ("MessageBroker/Kafka/Heartbeat/Receive", "present"),
        ("MessageBroker/Kafka/Heartbeat/SessionTimeout", "present"),
        ("MessageBroker/Kafka/Heartbeat/PollTimeout", "present"),
    ]
)
def test_fail_timeout_heartbeat_metrics_recorded():
    heartbeat = kafka.coordinator.heartbeat.Heartbeat(session_timeout_ms=0, max_poll_interval_ms=0)

    heartbeat.poll()
    heartbeat.sent_heartbeat()
    heartbeat.received_heartbeat()
    heartbeat.fail_heartbeat()

    assert heartbeat.session_timeout_expired(), "Failed to force heartbeat to timeout."
    assert heartbeat.poll_timeout_expired(), "Failed to force heartbeat to timeout."
