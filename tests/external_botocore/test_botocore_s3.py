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

import sys
import uuid

import botocore
import botocore.session
import moto
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

MOTO_VERSION = tuple(int(v) for v in moto.__version__.split(".")[:3])
BOTOCORE_VERSION = tuple(int(v) for v in botocore.__version__.split(".")[:3])


# patch earlier versions of moto to support py37
if sys.version_info >= (3, 7) and MOTO_VERSION <= (1, 3, 1):
    import re

    moto.packages.responses.responses.re._pattern_type = re.Pattern

AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"  # nosec
AWS_REGION = "us-east-1"

TEST_BUCKET = "python-agent-test-%s" % uuid.uuid4()
if BOTOCORE_VERSION >= (1, 28):
    S3_URL = "%s.s3.amazonaws.com" % TEST_BUCKET
    EXPECTED_BUCKET_URL = "https://%s/" % S3_URL
    EXPECTED_KEY_URL = EXPECTED_BUCKET_URL + "hello_world"
else:
    S3_URL = "s3.amazonaws.com"
    EXPECTED_BUCKET_URL = "https://%s/%s" % (S3_URL, TEST_BUCKET)
    EXPECTED_KEY_URL = EXPECTED_BUCKET_URL + "/hello_world"


_s3_scoped_metrics = [
    ("External/%s/botocore/GET" % S3_URL, 2),
    ("External/%s/botocore/PUT" % S3_URL, 2),
    ("External/%s/botocore/DELETE" % S3_URL, 2),
]

_s3_rollup_metrics = [
    ("External/all", 6),
    ("External/allOther", 6),
    ("External/%s/all" % S3_URL, 6),
    ("External/%s/botocore/GET" % S3_URL, 2),
    ("External/%s/botocore/PUT" % S3_URL, 2),
    ("External/%s/botocore/DELETE" % S3_URL, 2),
]


@override_application_settings({"distributed_tracing.enabled": True})
@validate_span_events(exact_agents={"aws.operation": "CreateBucket"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "PutObject"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "ListObjects"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "GetObject"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteObject"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteBucket"}, count=1)
@validate_span_events(exact_agents={"http.url": EXPECTED_BUCKET_URL}, count=3)
@validate_span_events(exact_agents={"http.url": EXPECTED_KEY_URL}, count=3)
@validate_transaction_metrics(
    "test_botocore_s3:test_s3",
    scoped_metrics=_s3_scoped_metrics,
    rollup_metrics=_s3_rollup_metrics,
    background_task=True,
)
@background_task()
@moto.mock_s3
def test_s3():
    session = botocore.session.get_session()
    client = session.create_client(
        "s3", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Create bucket
    resp = client.create_bucket(Bucket=TEST_BUCKET)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Put object
    resp = client.put_object(Bucket=TEST_BUCKET, Key="hello_world", Body=b"hello_world_content")
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # List bucket
    resp = client.list_objects(Bucket=TEST_BUCKET)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp["Contents"]) == 1
    assert resp["Contents"][0]["Key"] == "hello_world"

    # Get object
    resp = client.get_object(Bucket=TEST_BUCKET, Key="hello_world")
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["Body"].read() == b"hello_world_content"

    # Delete object
    resp = client.delete_object(Bucket=TEST_BUCKET, Key="hello_world")
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204

    # Delete bucket
    resp = client.delete_bucket(Bucket=TEST_BUCKET)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204
