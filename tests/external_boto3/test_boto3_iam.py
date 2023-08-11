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

import boto3
import moto
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)
from testing_support.validators.validate_tt_segment_params import (
    validate_tt_segment_params,
)

from newrelic.api.background_task import background_task

MOTO_VERSION = tuple(int(v) for v in moto.__version__.split(".")[:3])

# patch earlier versions of moto to support py37
if sys.version_info >= (3, 7) and MOTO_VERSION <= (1, 3, 1):
    import re

    moto.packages.responses.responses.re._pattern_type = re.Pattern

AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"  # nosec (This is fine for testing purposes)

TEST_USER = "python-agent-test-%s" % uuid.uuid4()

_iam_scoped_metrics = [
    ("External/iam.amazonaws.com/botocore/POST", 3),
]

_iam_rollup_metrics = [
    ("External/all", 3),
    ("External/allOther", 3),
    ("External/iam.amazonaws.com/all", 3),
    ("External/iam.amazonaws.com/botocore/POST", 3),
]


@override_application_settings({"distributed_tracing.enabled": True})
@validate_span_events(exact_agents={"http.url": "https://iam.amazonaws.com/"}, count=3)
@validate_span_events(expected_agents=("aws.requestId",), count=3)
@validate_span_events(exact_agents={"aws.operation": "CreateUser"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "GetUser"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteUser"}, count=1)
@validate_tt_segment_params(present_params=("aws.requestId",))
@validate_transaction_metrics(
    "test_boto3_iam:test_iam",
    scoped_metrics=_iam_scoped_metrics,
    rollup_metrics=_iam_rollup_metrics,
    background_task=True,
)
@background_task()
@moto.mock_iam
def test_iam():
    iam = boto3.client(
        "iam",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    # Create user
    resp = iam.create_user(UserName=TEST_USER)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Get the user
    resp = iam.get_user(UserName=TEST_USER)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["User"]["UserName"] == TEST_USER

    # Delete the user
    resp = iam.delete_user(UserName=TEST_USER)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
