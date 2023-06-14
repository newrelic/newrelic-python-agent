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

import botocore.session
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
AWS_REGION = "us-east-1"

TEST_TABLE = "python-agent-test-%s" % uuid.uuid4()


_dynamodb_scoped_metrics = [
    ("Datastore/statement/DynamoDB/%s/create_table" % TEST_TABLE, 1),
    ("Datastore/statement/DynamoDB/%s/put_item" % TEST_TABLE, 1),
    ("Datastore/statement/DynamoDB/%s/get_item" % TEST_TABLE, 1),
    ("Datastore/statement/DynamoDB/%s/update_item" % TEST_TABLE, 1),
    ("Datastore/statement/DynamoDB/%s/query" % TEST_TABLE, 1),
    ("Datastore/statement/DynamoDB/%s/scan" % TEST_TABLE, 1),
    ("Datastore/statement/DynamoDB/%s/delete_item" % TEST_TABLE, 1),
    ("Datastore/statement/DynamoDB/%s/delete_table" % TEST_TABLE, 1),
]

_dynamodb_rollup_metrics = [
    ("Datastore/all", 8),
    ("Datastore/allOther", 8),
    ("Datastore/DynamoDB/all", 8),
    ("Datastore/DynamoDB/allOther", 8),
]


@override_application_settings({"distributed_tracing.enabled": True})
@validate_span_events(expected_agents=("aws.requestId",), count=8)
@validate_span_events(exact_agents={"aws.operation": "PutItem"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "GetItem"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteItem"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "CreateTable"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteTable"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "Query"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "Scan"}, count=1)
@validate_tt_segment_params(present_params=("aws.requestId",))
@validate_transaction_metrics(
    "test_botocore_dynamodb:test_dynamodb",
    scoped_metrics=_dynamodb_scoped_metrics,
    rollup_metrics=_dynamodb_rollup_metrics,
    background_task=True,
)
@background_task()
@moto.mock_dynamodb2
def test_dynamodb():
    session = botocore.session.get_session()
    client = session.create_client(
        "dynamodb",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    # Create table
    resp = client.create_table(
        TableName=TEST_TABLE,
        AttributeDefinitions=[
            {"AttributeName": "Id", "AttributeType": "N"},
            {"AttributeName": "Foo", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "Id", "KeyType": "HASH"},
            {"AttributeName": "Foo", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5,
        },
    )
    assert resp["TableDescription"]["TableName"] == TEST_TABLE
    # moto response is ACTIVE, AWS response is CREATING
    # assert resp['TableDescription']['TableStatus'] == 'ACTIVE'

    # # AWS needs time to create the table
    # import time
    # time.sleep(15)

    # Put item
    resp = client.put_item(
        TableName=TEST_TABLE,
        Item={
            "Id": {"N": "101"},
            "Foo": {"S": "hello_world"},
            "SomeValue": {"S": "some_random_attribute"},
        },
    )
    # No checking response, due to inconsistent return values.
    # moto returns resp['Attributes']. AWS returns resp['ResponseMetadata']

    # Get item
    resp = client.get_item(
        TableName=TEST_TABLE,
        Key={
            "Id": {"N": "101"},
            "Foo": {"S": "hello_world"},
            "SomeValue": {"S": "some_random_attribute"},
        },
    )
    assert resp["Item"]["SomeValue"]["S"] == "some_random_attribute"

    # Update item
    resp = client.update_item(
        TableName=TEST_TABLE,
        Key={
            "Id": {"N": "101"},
            "Foo": {"S": "hello_world"},
            "SomeValue": {"S": "some_random_attribute"},
        },
        AttributeUpdates={
            "Foo2": {"Value": {"S": "hello_world2"}, "Action": "PUT"},
        },
        ReturnValues="ALL_NEW",
    )
    assert resp["Attributes"]["Foo2"]

    # Query for item
    resp = client.query(
        TableName=TEST_TABLE,
        Select="ALL_ATTRIBUTES",
        KeyConditionExpression="#Id = :v_id",
        ExpressionAttributeNames={"#Id": "Id"},
        ExpressionAttributeValues={":v_id": {"N": "101"}},
    )
    assert len(resp["Items"]) == 1
    assert resp["Items"][0]["SomeValue"]["S"] == "some_random_attribute"

    # Scan
    resp = client.scan(TableName=TEST_TABLE)
    assert len(resp["Items"]) == 1

    # Delete item
    resp = client.delete_item(
        TableName=TEST_TABLE,
        Key={
            "Id": {"N": "101"},
            "Foo": {"S": "hello_world"},
        },
    )
    # No checking response, due to inconsistent return values.
    # moto returns resp['Attributes']. AWS returns resp['ResponseMetadata']

    # Delete table
    resp = client.delete_table(TableName=TEST_TABLE)
    assert resp["TableDescription"]["TableName"] == TEST_TABLE
    # moto response is ACTIVE, AWS response is DELETING
    # assert resp['TableDescription']['TableStatus'] == 'DELETING'
