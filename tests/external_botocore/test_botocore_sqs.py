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

import uuid

import botocore.session
import pytest
from moto import mock_aws
from testing_support.fixtures import dt_enabled
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

MOTO_VERSION = get_package_version_tuple("moto")
BOTOCORE_VERSION = get_package_version_tuple("botocore")

url = "sqs.us-east-1.amazonaws.com"
EXPECTED_SEND_MESSAGE_AGENT_ATTRS = {
    "expected_agents": ["messaging.destination.name"],
    "exact_agents": {
        "aws.operation": "SendMessage",
        "cloud.account.id": "123456789012",
        "cloud.region": "us-east-1",
        "messaging.system": "aws_sqs",
    },
}
EXPECTED_RECIEVE_MESSAGE_AGENT_ATTRS = {
    "expected_agents": ["messaging.destination.name"],
    "exact_agents": {
        "aws.operation": "ReceiveMessage",
        "cloud.account.id": "123456789012",
        "cloud.region": "us-east-1",
        "messaging.system": "aws_sqs",
    },
}
EXPECTED_SEND_MESSAGE_BATCH_AGENT_ATTRS = required = {
    "expected_agents": ["messaging.destination.name"],
    "exact_agents": {
        "aws.operation": "SendMessageBatch",
        "cloud.account.id": "123456789012",
        "cloud.region": "us-east-1",
        "messaging.system": "aws_sqs",
    },
}
if BOTOCORE_VERSION < (1, 29, 0):
    url = "queue.amazonaws.com"
    # The old style url does not contain the necessary AWS info.
    EXPECTED_SEND_MESSAGE_AGENT_ATTRS = {"exact_agents": {"aws.operation": "SendMessage"}}
    EXPECTED_RECIEVE_MESSAGE_AGENT_ATTRS = {"exact_agents": {"aws.operation": "ReceiveMessage"}}
    EXPECTED_SEND_MESSAGE_BATCH_AGENT_ATTRS = {"exact_agents": {"aws.operation": "SendMessageBatch"}}

AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"  # nosec
AWS_REGION = "us-east-1"

TEST_QUEUE = f"python-agent-test-{uuid.uuid4()}"


_sqs_scoped_metrics = [(f"MessageBroker/SQS/Queue/Produce/Named/{TEST_QUEUE}", 2), (f"External/{url}/botocore/POST", 3)]

_sqs_rollup_metrics = [
    (f"MessageBroker/SQS/Queue/Produce/Named/{TEST_QUEUE}", 2),
    (f"MessageBroker/SQS/Queue/Consume/Named/{TEST_QUEUE}", 1),
    ("External/all", 3),
    ("External/allOther", 3),
    (f"External/{url}/all", 3),
    (f"External/{url}/botocore/POST", 3),
]

_sqs_scoped_metrics_malformed = [("MessageBroker/SQS/Queue/Produce/Named/Unknown", 1)]

_sqs_rollup_metrics_malformed = [("MessageBroker/SQS/Queue/Produce/Named/Unknown", 1)]


@dt_enabled
@validate_span_events(exact_agents={"aws.operation": "CreateQueue"}, count=1)
@validate_span_events(**EXPECTED_SEND_MESSAGE_AGENT_ATTRS, count=1)
@validate_span_events(**EXPECTED_RECIEVE_MESSAGE_AGENT_ATTRS, count=1)
@validate_span_events(**EXPECTED_SEND_MESSAGE_BATCH_AGENT_ATTRS, count=1)
@validate_span_events(exact_agents={"aws.operation": "PurgeQueue"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteQueue"}, count=1)
@validate_transaction_metrics(
    "test_botocore_sqs:test_sqs",
    scoped_metrics=_sqs_scoped_metrics,
    rollup_metrics=_sqs_rollup_metrics,
    background_task=True,
)
@background_task()
@mock_aws
def test_sqs():
    session = botocore.session.get_session()
    client = session.create_client(
        "sqs", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Create queue
    resp = client.create_queue(QueueName=TEST_QUEUE)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # QueueUrl is needed for rest of methods.
    QUEUE_URL = resp["QueueUrl"]

    # Send message
    resp = client.send_message(QueueUrl=QUEUE_URL, MessageBody="hello_world")
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Receive message
    resp = client.receive_message(QueueUrl=QUEUE_URL)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Send message batch
    messages = [
        {"Id": "1", "MessageBody": "message 1"},
        {"Id": "2", "MessageBody": "message 2"},
        {"Id": "3", "MessageBody": "message 3"},
    ]
    resp = client.send_message_batch(QueueUrl=QUEUE_URL, Entries=messages)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Purge queue
    resp = client.purge_queue(QueueUrl=QUEUE_URL)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Delete queue
    resp = client.delete_queue(QueueUrl=QUEUE_URL)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@dt_enabled
@validate_transaction_metrics(
    "test_botocore_sqs:test_sqs_malformed",
    scoped_metrics=_sqs_scoped_metrics_malformed,
    rollup_metrics=_sqs_rollup_metrics_malformed,
    background_task=True,
)
@background_task()
@mock_aws
def test_sqs_malformed():
    session = botocore.session.get_session()
    client = session.create_client(
        "sqs", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Malformed send message, uses arg instead of kwarg
    with pytest.raises(TypeError):
        client.send_message("https://fake-url/", MessageBody="hello_world")
