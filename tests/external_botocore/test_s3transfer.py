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

import os
import uuid

import boto3
import botocore
from moto import mock_aws
from testing_support.fixtures import dt_enabled
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

MOTO_VERSION = get_package_version_tuple("moto")
BOTOCORE_VERSION = get_package_version_tuple("botocore")

AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"  # nosec
AWS_REGION_NAME = "us-west-2"

TEST_BUCKET = f"python-agent-test-{uuid.uuid4()}"

if BOTOCORE_VERSION < (1, 7, 41):
    S3_URL = "s3-us-west-2.amazonaws.com"
    EXPECTED_BUCKET_URL = f"https://{S3_URL}/{TEST_BUCKET}"
    EXPECTED_KEY_URL = f"{EXPECTED_BUCKET_URL}/hello_world"
elif BOTOCORE_VERSION < (1, 28):
    S3_URL = "s3.us-west-2.amazonaws.com"
    EXPECTED_BUCKET_URL = f"https://{S3_URL}/{TEST_BUCKET}"
    EXPECTED_KEY_URL = f"{EXPECTED_BUCKET_URL}/hello_world"
else:
    S3_URL = f"{TEST_BUCKET}.s3.us-west-2.amazonaws.com"
    EXPECTED_BUCKET_URL = f"https://{S3_URL}/"
    EXPECTED_KEY_URL = f"{EXPECTED_BUCKET_URL}hello_world"


@dt_enabled
@validate_span_events(exact_agents={"aws.operation": "CreateBucket"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "PutObject"}, count=1)
@validate_transaction_metrics(
    "test_s3transfer:test_s3_context_propagation",
    scoped_metrics=[(f"External/{S3_URL}/botocore/PUT", 2)],
    rollup_metrics=[
        ("External/all", 2),
        ("External/allOther", 2),
        (f"External/{S3_URL}/all", 2),
        (f"External/{S3_URL}/botocore/PUT", 2),
    ],
    background_task=True,
)
@background_task()
@mock_aws
def test_s3_context_propagation():
    client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION_NAME,
    )

    # Create bucket
    resp = client.create_bucket(Bucket=TEST_BUCKET, CreateBucketConfiguration={"LocationConstraint": AWS_REGION_NAME})
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Upload file
    test_file = os.path.join(os.path.dirname(__file__), "_test_file.txt")
    client.upload_file(Filename=test_file, Bucket=TEST_BUCKET, Key="_test_file.txt")
    # No return value to check for this function currently
