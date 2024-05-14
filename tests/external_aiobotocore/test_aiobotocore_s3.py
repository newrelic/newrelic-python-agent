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

import aiobotocore
from conftest import (  # noqa: F401, pylint: disable=W0611
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    PORT,
    MotoService,
    loop,
)
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

TEST_BUCKET = "python-agent-test"
FILENAME = "dummy.bin"
FOLDER = "aiobotocore"
ENDPOINT = "localhost:%s" % PORT
KEY = "{}/{}".format(FOLDER, FILENAME)
EXPECTED_BUCKET_URL = "http://%s/%s" % (ENDPOINT, TEST_BUCKET)
EXPECTED_KEY_URL = EXPECTED_BUCKET_URL + "/" + KEY


_s3_scoped_metrics = [
    ("External/%s/aiobotocore/GET" % ENDPOINT, 5),
    ("External/%s/aiobotocore/PUT" % ENDPOINT, 2),
    ("External/%s/aiobotocore/DELETE" % ENDPOINT, 2),
]

_s3_rollup_metrics = [
    ("External/all", 9),
    ("External/allOther", 9),
    ("External/%s/all" % ENDPOINT, 9),
    ("External/%s/aiobotocore/GET" % ENDPOINT, 5),
    ("External/%s/aiobotocore/PUT" % ENDPOINT, 2),
    ("External/%s/aiobotocore/DELETE" % ENDPOINT, 2),
]


@validate_span_events(exact_agents={"aws.operation": "CreateBucket"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "PutObject"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "ListObjects"}, count=2)
@validate_span_events(exact_agents={"aws.operation": "GetObject"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteBucket"}, count=1)
@validate_span_events(exact_agents={"http.url": EXPECTED_BUCKET_URL}, count=4)
@validate_span_events(exact_agents={"http.url": EXPECTED_KEY_URL}, count=4)
@validate_transaction_metrics(
    "test_aiobotocore_s3:test_aiobotocore_s3",
    scoped_metrics=_s3_scoped_metrics,
    rollup_metrics=_s3_rollup_metrics,
    background_task=True,
)
@background_task()
def test_aiobotocore_s3(loop):
    async def _test():

        data = b"hello_world"

        async with MotoService("s3", port=PORT):

            session = aiobotocore.session.get_session()

            async with session.create_client(  # nosec
                "s3",
                region_name="us-east-1",
                endpoint_url="http://localhost:%d" % PORT,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            ) as client:

                # Create bucket
                await client.create_bucket(
                    Bucket=TEST_BUCKET,
                )

                # List buckets
                await client.list_buckets()

                # Upload object to s3
                resp = await client.put_object(Bucket=TEST_BUCKET, Key=KEY, Body=data)
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

                # List objects from bucket
                await client.list_objects(Bucket=TEST_BUCKET)

                # Getting s3 object properties of uploaded file
                resp = await client.get_object_acl(Bucket=TEST_BUCKET, Key=KEY)
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

                # Get object from s3
                response = await client.get_object(Bucket=TEST_BUCKET, Key=KEY)
                # this will ensure the connection is correctly re-used/closed
                async with response["Body"] as stream:
                    assert await stream.read() == data

                # List s3 objects using paginator
                paginator = client.get_paginator("list_objects")
                async for result in paginator.paginate(Bucket=TEST_BUCKET, Prefix=FOLDER):
                    for content in result.get("Contents", []):
                        assert content

                # Delete object from s3
                await client.delete_object(Bucket=TEST_BUCKET, Key=KEY)

                # Delete bucket from s3
                await client.delete_bucket(Bucket=TEST_BUCKET)

    loop.run_until_complete(_test())
