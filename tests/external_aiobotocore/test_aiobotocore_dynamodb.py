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

from aiobotocore.session import get_session
from conftest import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, PORT, MotoService, loop
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

TEST_TABLE = "python-agent-test"

_dynamodb_scoped_metrics = [
    (f"Datastore/statement/DynamoDB/{TEST_TABLE}/create_table", 1),
    (f"Datastore/statement/DynamoDB/{TEST_TABLE}/put_item", 1),
    (f"Datastore/statement/DynamoDB/{TEST_TABLE}/get_item", 1),
    (f"Datastore/statement/DynamoDB/{TEST_TABLE}/update_item", 1),
    (f"Datastore/statement/DynamoDB/{TEST_TABLE}/query", 1),
    (f"Datastore/statement/DynamoDB/{TEST_TABLE}/scan", 1),
    (f"Datastore/statement/DynamoDB/{TEST_TABLE}/delete_item", 1),
    (f"Datastore/statement/DynamoDB/{TEST_TABLE}/delete_table", 1),
]

_dynamodb_rollup_metrics = [
    ("Datastore/all", 8),
    ("Datastore/allOther", 8),
    ("Datastore/DynamoDB/all", 8),
    ("Datastore/DynamoDB/allOther", 8),
]


# aws.requestId count disabled due to variability in count.
# Flaky due to waiter function, which "aws.operation" == "DescribeTable"
# This is a polling function, so in real time, this value could fluctuate
# @validate_span_events(expected_agents=("aws.requestId",), count=9)
# @validate_span_events(exact_agents={"aws.operation": "DescribeTable"}, count=2)
@validate_span_events(exact_agents={"aws.operation": "PutItem"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "GetItem"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteItem"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "CreateTable"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteTable"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "Query"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "Scan"}, count=1)
@validate_transaction_metrics(
    "test_aiobotocore_dynamodb:test_aiobotocore_dynamodb",
    scoped_metrics=_dynamodb_scoped_metrics,
    rollup_metrics=_dynamodb_rollup_metrics,
    background_task=True,
)
@background_task()
def test_aiobotocore_dynamodb(loop):
    async def _test():
        async with MotoService("dynamodb", port=PORT):
            session = get_session()

            async with session.create_client(
                "dynamodb",
                region_name="us-east-1",
                endpoint_url=f"http://localhost:{PORT}",
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            ) as client:
                resp = await client.create_table(
                    TableName=TEST_TABLE,
                    AttributeDefinitions=[
                        {"AttributeName": "Id", "AttributeType": "N"},
                        {"AttributeName": "Foo", "AttributeType": "S"},
                    ],
                    KeySchema=[
                        {"AttributeName": "Id", "KeyType": "HASH"},
                        {"AttributeName": "Foo", "KeyType": "RANGE"},
                    ],
                    ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                )
                assert resp["TableDescription"]["TableName"] == TEST_TABLE

                # Wait for table to be created
                waiter = client.get_waiter("table_exists")
                await waiter.wait(TableName=TEST_TABLE)

                # Put item
                resp = await client.put_item(
                    TableName=TEST_TABLE, Item={"Id": {"N": "101"}, "Foo": {"S": "hello_world"}}
                )
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

                # Get item
                resp = await client.get_item(
                    TableName=TEST_TABLE, Key={"Id": {"N": "101"}, "Foo": {"S": "hello_world"}}
                )
                assert resp["Item"]["Foo"]["S"] == "hello_world"

                # Update item
                resp = await client.update_item(
                    TableName=TEST_TABLE,
                    Key={"Id": {"N": "101"}, "Foo": {"S": "hello_world"}},
                    AttributeUpdates={"Foo2": {"Value": {"S": "hello_world2"}, "Action": "PUT"}},
                    ReturnValues="ALL_NEW",
                )
                assert resp["Attributes"]["Foo2"]

                # Query for item
                resp = await client.query(
                    TableName=TEST_TABLE,
                    Select="ALL_ATTRIBUTES",
                    KeyConditionExpression="#Id = :v_id",
                    ExpressionAttributeNames={"#Id": "Id"},
                    ExpressionAttributeValues={":v_id": {"N": "101"}},
                )
                assert len(resp["Items"]) == 1
                assert resp["Items"][0]["Foo"]["S"] == "hello_world"

                # Scan
                resp = await client.scan(TableName=TEST_TABLE)
                assert len(resp["Items"]) == 1

                # Delete item
                resp = await client.delete_item(
                    TableName=TEST_TABLE, Key={"Id": {"N": "101"}, "Foo": {"S": "hello_world"}}
                )
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

                # Delete table
                resp = await client.delete_table(TableName=TEST_TABLE)
                assert resp["TableDescription"]["TableName"] == TEST_TABLE

    loop.run_until_complete(_test())
