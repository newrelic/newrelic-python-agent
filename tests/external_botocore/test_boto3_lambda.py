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

import io
import json
import zipfile

import boto3
import pytest
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

LAMBDA_URL = "lambda.us-west-2.amazonaws.com"
EXPECTED_LAMBDA_URL = f"https://{LAMBDA_URL}/2015-03-31/functions"
LAMBDA_ARN = f"arn:aws:lambda:{AWS_REGION_NAME}:383735328703:function:lambdaFunction"


_lambda_scoped_metrics = [(f"External/{LAMBDA_URL}/botocore/POST", 2)]

_lambda_rollup_metrics = [
    ("External/all", 3),
    ("External/allOther", 3),
    (f"External/{LAMBDA_URL}/all", 2),
    (f"External/{LAMBDA_URL}/botocore/POST", 2),
]


@dt_enabled
@validate_span_events(exact_agents={"aws.operation": "CreateFunction"}, count=1)
@validate_span_events(
    exact_agents={"aws.operation": "Invoke", "cloud.platform": "aws_lambda", "cloud.resource_id": LAMBDA_ARN}, count=1
)
@validate_span_events(exact_agents={"aws.operation": "Invoke"}, count=1)
@validate_span_events(exact_agents={"http.url": EXPECTED_LAMBDA_URL}, count=1)
@validate_transaction_metrics(
    "test_boto3_lambda:test_lambda",
    scoped_metrics=_lambda_scoped_metrics,
    rollup_metrics=_lambda_rollup_metrics,
    background_task=True,
)
@background_task()
@mock_aws
def test_lambda(iam_role_arn, lambda_zip):
    role_arn = iam_role_arn()

    client = boto3.client(
        "lambda",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION_NAME,
    )

    # Create lambda
    resp = client.create_function(
        FunctionName="lambdaFunction", Runtime="python3.9", Role=role_arn, Code={"ZipFile": lambda_zip}
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 201

    # Invoke lambda
    client.invoke(FunctionName=LAMBDA_ARN, InvocationType="RequestResponse", Payload=json.dumps({}))
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 201


@pytest.fixture
def lambda_zip():
    code = """
        def lambda_handler(event, context):
            return event
        """
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", code)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


@pytest.fixture
def iam_role_arn():
    def create_role():
        iam = boto3.client(
            "iam",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME,
        )
        # Create IAM role
        role = iam.create_role(RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/")
        return role["Role"]["Arn"]

    return create_role
