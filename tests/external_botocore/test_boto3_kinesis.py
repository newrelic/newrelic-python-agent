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

import boto3
import pytest
from moto import mock_aws
from testing_support.fixtures import dt_enabled
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

MOTO_VERSION = get_package_version_tuple("moto")
BOTOCORE_VERSION = get_package_version_tuple("boto3")

URL = "kinesis.us-east-1.amazonaws.com"
TEST_STREAM = f"python-agent-test-{uuid.uuid4()}"
EXPECTED_AGENT_ATTRS = {
    "exact_agents": {
        "cloud.platform": "aws_kinesis_data_streams",
        "cloud.resource_id": f"arn:aws:kinesis:us-east-1:123456789012:stream/{TEST_STREAM}",
    },
}
# if BOTOCORE_VERSION < (1, 29, 0):
#    URL = "queue.amazonaws.com"
#    # The old style URL does not contain the necessary AWS info.
#    EXPECTED_SEND_MESSAGE_AGENT_ATTRS = {
#        "exact_agents": {
#            "aws.operation": "SendMessage",
#        },
#    }
#    EXPECTED_RECIEVE_MESSAGE_AGENT_ATTRS = {
#        "exact_agents": {
#            "aws.operation": "ReceiveMessage",
#        },
#    }
#    EXPECTED_SEND_MESSAGE_BATCH_AGENT_ATTRS = {
#        "exact_agents": {
#            "aws.operation": "SendMessageBatch",
#        },
#    }

AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"  # nosec
AWS_REGION = "us-east-1"

_kinesis_scoped_metrics = [
    (f"MessageBroker/Kinesis/Stream/Produce/Named/{TEST_STREAM}", 2),
    (f"External/{URL}/botocore/POST", 2),
]

_kinesis_rollup_metrics = [
    (f"MessageBroker/Kinesis/Stream/Produce/Named/{TEST_STREAM}", 2),
    (f"MessageBroker/Kinesis/Stream/Consume/Named/{TEST_STREAM}", 1),
    ("External/all", 4),
    ("External/allOther", 4),
    (f"External/{URL}/all", 2),
    (f"External/{URL}/botocore/POST", 2),
]

_kinesis_scoped_metrics_error = [
    ("MessageBroker/Kinesis/Stream/Produce/Named/Unknown", 1),
]

_kinesis_rollup_metrics_error = [
    ("MessageBroker/Kinesis/Stream/Produce/Named/Unknown", 1),
]


@dt_enabled
@validate_span_events(exact_agents={"aws.operation": "CreateStream"}, count=1)
@validate_span_events(
    **EXPECTED_AGENT_ATTRS,
    count=3,
)
@validate_span_events(exact_agents={"aws.operation": "DeleteStream"}, count=1)
@validate_transaction_metrics(
    "test_boto3_kinesis:test_kinesis",
    scoped_metrics=_kinesis_scoped_metrics,
    rollup_metrics=_kinesis_rollup_metrics,
    background_task=True,
)
@background_task()
@mock_aws
def test_kinesis():
    client = boto3.client(
        "kinesis",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    # Create stream
    resp = client.create_stream(StreamName=TEST_STREAM, ShardCount=123, StreamModeDetails={"StreamMode": "on-demand"})
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Stream ARN is needed for rest of methods.
    resp = client.describe_stream(
        StreamName=TEST_STREAM,
        Limit=123,
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    ARN = resp["StreamDescription"]["StreamARN"]

    # Send message
    resp = client.put_record(Data=b"foo1", PartitionKey="bar", StreamARN=ARN)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Send messages
    resp = client.put_records(
        Records=[{"Data": b"foo2", "PartitionKey": "bar"}, {"Data": b"foo3", "PartitionKey": "bar"}], StreamARN=ARN
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    shard_iter = client.get_shard_iterator(
        ShardId="shardId-000000000000",
        ShardIteratorType="AT_SEQUENCE_NUMBER",
        StartingSequenceNumber="0",
        StreamARN=ARN,
    )["ShardIterator"]

    # Receive message
    resp = client.get_records(ShardIterator=shard_iter, StreamARN=ARN)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Delete stream
    resp = client.delete_stream(
        EnforceConsumerDeletion=True,
        StreamARN=ARN,
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@dt_enabled
@validate_transaction_metrics(
    "test_boto3_kinesis:test_kinesis_error",
    scoped_metrics=_kinesis_scoped_metrics_error,
    rollup_metrics=_kinesis_rollup_metrics_error,
    background_task=True,
)
@background_task()
@mock_aws
def test_kinesis_error():
    client = boto3.client(
        "kinesis",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    # Create stream
    resp = client.create_stream(StreamName=TEST_STREAM, ShardCount=123, StreamModeDetails={"StreamMode": "on-demand"})
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Stream ARN is needed for rest of methods.
    resp = client.describe_stream(
        StreamName=TEST_STREAM,
        Limit=123,
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    ARN = resp["StreamDescription"]["StreamARN"]

    # Malformed send message, uses arg instead of kwarg
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        resp = client.put_record(
            Data=b"{foo}",
            PartitionKey="bar",
        )

    # Delete stream
    resp = client.delete_stream(
        EnforceConsumerDeletion=True,
        StreamARN=ARN,
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
