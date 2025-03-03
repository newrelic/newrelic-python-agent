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

URL = "firehose.us-east-1.amazonaws.com"
TEST_STREAM = f"python-agent-test-{uuid.uuid4()}"
TEST_STREAM_ARN = f"arn:aws:firehose:us-east-1:123456789012:deliverystream/{TEST_STREAM}"
TEST_S3_BUCKET = f"python-agent-test-{uuid.uuid4()}"
TEST_S3_BUCKET_ARN = f"arn:aws:s3:::{TEST_S3_BUCKET}"
TEST_S3_ROLE_ARN = f"arn:aws:iam::123456789012:role/test-role"
EXPECTED_AGENT_ATTRS = {
    "exact_agents": {"cloud.platform": "aws_kinesis_delivery_streams", "cloud.resource_id": TEST_STREAM_ARN}
}

AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"  # nosec
AWS_REGION = "us-east-1"

_firehose_scoped_metrics = [
    (f"Firehose/create_delivery_stream/{TEST_STREAM}", 1),
    (f"Firehose/put_record/{TEST_STREAM}", 1),
    (f"Firehose/put_record_batch/{TEST_STREAM}", 1),
    (f"Firehose/describe_delivery_stream/{TEST_STREAM}", 1),
    (f"Firehose/list_delivery_streams", 1),
    (f"Firehose/delete_delivery_stream/{TEST_STREAM}", 1),
    (f"External/{URL}/botocore/POST", 6),
]

_firehose_rollup_metrics = [
    (f"Firehose/create_delivery_stream/{TEST_STREAM}", 1),
    (f"Firehose/put_record/{TEST_STREAM}", 1),
    (f"Firehose/put_record_batch/{TEST_STREAM}", 1),
    (f"Firehose/describe_delivery_stream/{TEST_STREAM}", 1),
    (f"Firehose/list_delivery_streams", 1),
    (f"Firehose/delete_delivery_stream/{TEST_STREAM}", 1),
    ("External/all", 7),  # Includes creating S3 bucket
    ("External/allOther", 7),
    (f"External/{URL}/all", 6),
    (f"External/{URL}/botocore/POST", 6),
]

_firehose_scoped_metrics_error = [(f"Firehose/put_record/{TEST_STREAM}", 1)]

_firehose_rollup_metrics_error = [(f"Firehose/put_record/{TEST_STREAM}", 1)]


@background_task()
@mock_aws
def test_instrumented_firehose_methods():
    client = boto3.client(
        "firehose",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    ignored_methods = set(
        ("firehose", method)
        for method in ("generate_presigned_url", "close", "get_waiter", "can_paginate", "get_paginator")
    )
    client_methods = inspect.getmembers(client, predicate=inspect.ismethod)
    methods = {("firehose", name) for (name, method) in client_methods if not name.startswith("_")}

    uninstrumented_methods = methods - set(CUSTOM_TRACE_POINTS.keys()) - ignored_methods
    assert not uninstrumented_methods


@override_application_settings({"cloud.aws.account_id": 123456789012})
@dt_enabled
@validate_span_events(exact_agents={"aws.operation": "CreateDeliveryStream"}, count=1)
@validate_span_events(**EXPECTED_AGENT_ATTRS, count=5)
@validate_span_events(exact_agents={"aws.operation": "DeleteDeliveryStream"}, count=1)
@validate_transaction_metrics(
    "test_boto3_firehose:test_firehose",
    scoped_metrics=_firehose_scoped_metrics,
    rollup_metrics=_firehose_rollup_metrics,
    background_task=True,
)
@background_task()
@mock_aws
def test_firehose(firehose_destination):
    client = boto3.client(
        "firehose",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    destination_kwargs = firehose_destination()

    # Create stream
    resp = client.create_delivery_stream(
        DeliveryStreamName=TEST_STREAM, DeliveryStreamType="DirectPut", **destination_kwargs
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Call describe on delivery stream
    resp = client.describe_delivery_stream(DeliveryStreamName=TEST_STREAM, Limit=123)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["DeliveryStreamDescription"]["DeliveryStreamARN"] == TEST_STREAM_ARN

    # Call describe on delivery stream
    resp = client.list_delivery_streams(Limit=123)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Send message
    resp = client.put_record(Record={"Data": b"foo1"}, DeliveryStreamName=TEST_STREAM)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Send messages
    resp = client.put_record_batch(Records=[{"Data": b"foo2"}, {"Data": b"foo3"}], DeliveryStreamName=TEST_STREAM)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Delete stream
    resp = client.delete_delivery_stream(DeliveryStreamName=TEST_STREAM)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@dt_enabled
@validate_transaction_metrics(
    "test_boto3_firehose:test_firehose_error",
    scoped_metrics=_firehose_scoped_metrics_error,
    rollup_metrics=_firehose_rollup_metrics_error,
    background_task=True,
)
@background_task()
@mock_aws
def test_firehose_error(firehose_destination):
    client = boto3.client(
        "firehose",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    destination_kwargs = firehose_destination()

    # Create stream
    resp = client.create_delivery_stream(
        DeliveryStreamName=TEST_STREAM, DeliveryStreamType="DirectPut", **destination_kwargs
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Malformed send message, uses arg instead of kwarg
    with pytest.raises(TypeError):
        resp = client.put_record({"Data": b"foo"}, DeliveryStreamName=TEST_STREAM)

    # Delete stream
    resp = client.delete_delivery_stream(DeliveryStreamName=TEST_STREAM)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@pytest.fixture(scope="session")
def firehose_destination():
    def create_firehose_destination():
        import boto3

        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )

        resp = s3.create_bucket(Bucket=TEST_S3_BUCKET)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        return {"S3DestinationConfiguration": {"RoleARN": TEST_S3_ROLE_ARN, "BucketARN": TEST_S3_BUCKET_ARN}}

    return create_firehose_destination
