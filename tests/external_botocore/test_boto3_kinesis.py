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

import inspect
import uuid

import boto3
import botocore
import pytest
from moto import mock_aws
from testing_support.fixtures import dt_enabled, override_application_settings
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple
from newrelic.hooks.external_botocore import CUSTOM_TRACE_POINTS

MOTO_VERSION = get_package_version_tuple("moto")
BOTOCORE_VERSION = get_package_version_tuple("boto3")

AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"  # nosec
AWS_REGION = "us-east-1"
AWS_ACCOUNT_ID = 123456789012

KINESIS_URL = "kinesis.us-east-1.amazonaws.com"
KINESIS_CONTROL_URL = f"{AWS_ACCOUNT_ID}.control-kinesis.{AWS_REGION}.amazonaws.com"
KINESIS_DATA_URL = f"{AWS_ACCOUNT_ID}.data-kinesis.{AWS_REGION}.amazonaws.com"
TEST_STREAM = f"python-agent-test-{uuid.uuid4()}"
EXPECTED_AGENT_ATTRS = {
    "exact_agents": {
        "cloud.platform": "aws_kinesis_data_streams",
        "cloud.resource_id": f"arn:aws:kinesis:us-east-1:{AWS_ACCOUNT_ID}:stream/{TEST_STREAM}",
    }
}

_kinesis_scoped_metrics = [
    (f"MessageBroker/Kinesis/Stream/Produce/Named/{TEST_STREAM}", 2),
    (f"MessageBroker/Kinesis/Stream/Consume/Named/{TEST_STREAM}", 1),
    (f"Kinesis/create_stream/{TEST_STREAM}", 1),
    ("Kinesis/list_streams", 1),
    (f"Kinesis/describe_stream/{TEST_STREAM}", 1),
    (f"Kinesis/put_resource_policy/{TEST_STREAM}", 2),
    (f"Kinesis/get_shard_iterator/{TEST_STREAM}", 1),
    (f"Kinesis/delete_stream/{TEST_STREAM}", 1),
    (f"External/{KINESIS_URL}/botocore/POST", 3),
    (f"External/{KINESIS_CONTROL_URL}/botocore/POST", 3),
    (f"External/{KINESIS_DATA_URL}/botocore/POST", 1),
]
if BOTOCORE_VERSION < (1, 29, 0):
    _kinesis_scoped_metrics = [
        (f"MessageBroker/Kinesis/Stream/Produce/Named/{TEST_STREAM}", 2),
        (f"Kinesis/create_stream/{TEST_STREAM}", 1),
        ("Kinesis/list_streams", 1),
        (f"Kinesis/describe_stream/{TEST_STREAM}", 1),
        (f"Kinesis/get_shard_iterator/{TEST_STREAM}", 1),
        (f"Kinesis/delete_stream/{TEST_STREAM}", 1),
        (f"External/{KINESIS_URL}/botocore/POST", 5),
    ]

_kinesis_rollup_metrics = [
    (f"MessageBroker/Kinesis/Stream/Produce/Named/{TEST_STREAM}", 2),
    (f"MessageBroker/Kinesis/Stream/Consume/Named/{TEST_STREAM}", 1),
    (f"Kinesis/create_stream/{TEST_STREAM}", 1),
    ("Kinesis/list_streams", 1),
    (f"Kinesis/describe_stream/{TEST_STREAM}", 1),
    (f"Kinesis/put_resource_policy/{TEST_STREAM}", 2),
    (f"Kinesis/get_shard_iterator/{TEST_STREAM}", 1),
    (f"Kinesis/delete_stream/{TEST_STREAM}", 1),
    ("External/all", 7),
    ("External/allOther", 7),
    (f"External/{KINESIS_URL}/all", 3),
    (f"External/{KINESIS_URL}/botocore/POST", 3),
    (f"External/{KINESIS_CONTROL_URL}/all", 3),
    (f"External/{KINESIS_CONTROL_URL}/botocore/POST", 3),
    (f"External/{KINESIS_DATA_URL}/all", 1),
    (f"External/{KINESIS_DATA_URL}/botocore/POST", 1),
]
if BOTOCORE_VERSION < (1, 29, 0):
    _kinesis_rollup_metrics = [
        (f"MessageBroker/Kinesis/Stream/Produce/Named/{TEST_STREAM}", 2),
        (f"Kinesis/create_stream/{TEST_STREAM}", 1),
        ("Kinesis/list_streams", 1),
        (f"Kinesis/describe_stream/{TEST_STREAM}", 1),
        (f"Kinesis/get_shard_iterator/{TEST_STREAM}", 1),
        (f"Kinesis/delete_stream/{TEST_STREAM}", 1),
        ("External/all", 5),
        ("External/allOther", 5),
        (f"External/{KINESIS_URL}/all", 5),
        (f"External/{KINESIS_URL}/botocore/POST", 5),
    ]

_kinesis_scoped_metrics_error = [("MessageBroker/Kinesis/Stream/Produce/Named/Unknown", 1)]

_kinesis_rollup_metrics_error = [("MessageBroker/Kinesis/Stream/Produce/Named/Unknown", 1)]


@background_task()
@mock_aws
def test_instrumented_kinesis_methods():
    client = boto3.client(
        "kinesis",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    ignored_methods = set(
        ("kinesis", method)
        for method in ("generate_presigned_url", "close", "get_waiter", "can_paginate", "get_paginator")
    )
    client_methods = inspect.getmembers(client, predicate=inspect.ismethod)
    methods = {("kinesis", name) for (name, method) in client_methods if not name.startswith("_")}

    uninstrumented_methods = methods - set(CUSTOM_TRACE_POINTS.keys()) - ignored_methods
    assert not uninstrumented_methods


@override_application_settings({"cloud.aws.account_id": 123456789012})
@dt_enabled
@validate_span_events(exact_agents={"aws.operation": "CreateStream"}, count=1)
@validate_span_events(**EXPECTED_AGENT_ATTRS, count=6 if BOTOCORE_VERSION < (1, 29, 0) else 9)
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

    # List streams
    resp = client.list_streams(Limit=123)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Stream ARN is needed for rest of methods.
    resp = client.describe_stream(StreamName=TEST_STREAM, Limit=123)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    STREAM_ARN = resp["StreamDescription"]["StreamARN"]
    CONSUMER_ARN = f"{STREAM_ARN}/consumer/my_consumer:123"  # Mock ConsumerARN

    # StreamARN is not supported in older versions of botocore.
    stream_kwargs = {"StreamName": TEST_STREAM} if BOTOCORE_VERSION < (1, 29, 0) else {"StreamARN": STREAM_ARN}

    # Send message
    resp = client.put_record(Data=b"foo1", PartitionKey="bar", **stream_kwargs)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Send messages
    resp = client.put_records(
        Records=[{"Data": b"foo2", "PartitionKey": "bar"}, {"Data": b"foo3", "PartitionKey": "bar"}], **stream_kwargs
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Shards
    shard_iter = client.get_shard_iterator(
        ShardId="shardId-000000000000",
        ShardIteratorType="AT_SEQUENCE_NUMBER",
        StartingSequenceNumber="0",
        **stream_kwargs,
    )["ShardIterator"]

    # TODO: Unfortunately we can't test client.subscribe_to_shard() yet as moto has not implemented it.
    # It's the only method that uses ConsumerARN as a parameter name, so extracting that parameter can't be tested.
    # ResourceARN, however, can be tested and can be either a StreamARN or ConsumerARN format. We can therefore
    # at least cover the parsing of ConsumerARNs for the underlying stream by exercising that.

    if BOTOCORE_VERSION >= (1, 29, 0):
        # This was only made available in Botocore 1.29.0, no way to test ResourceARN before that
        # Use ResourceARN as StreamARN
        resp = client.put_resource_policy(ResourceARN=STREAM_ARN, Policy="some policy")
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        # Use ResourceARN as ConsumerARN
        resp = client.put_resource_policy(ResourceARN=CONSUMER_ARN, Policy="some policy")
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Receive message
    if BOTOCORE_VERSION < (1, 29, 0):
        resp = client.get_records(ShardIterator=shard_iter)
    else:
        resp = client.get_records(ShardIterator=shard_iter, **stream_kwargs)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Delete stream
    resp = client.delete_stream(EnforceConsumerDeletion=True, **stream_kwargs)
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
    resp = client.describe_stream(StreamName=TEST_STREAM, Limit=123)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    ARN = resp["StreamDescription"]["StreamARN"]

    # StreamARN is not supported in older versions of botocore.
    stream_kwargs = {"StreamName": TEST_STREAM} if BOTOCORE_VERSION < (1, 29, 0) else {"StreamARN": ARN}

    expected_error = (
        botocore.exceptions.ParamValidationError
        if BOTOCORE_VERSION < (1, 29, 0)
        else client.exceptions.ResourceNotFoundException
    )

    # Malformed send message, uses arg instead of kwarg
    with pytest.raises(expected_error):
        resp = client.put_record(Data=b"{foo}", PartitionKey="bar")

    # Delete stream
    resp = client.delete_stream(EnforceConsumerDeletion=True, **stream_kwargs)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
