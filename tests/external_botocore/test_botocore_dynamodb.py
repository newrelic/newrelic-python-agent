import uuid

import botocore.session
import moto

from newrelic.agent import background_task
from testing_support.fixtures import validate_transaction_metrics


AWS_ACCESS_KEY_ID = 'AAAAAAAAAAAACCESSKEY'
AWS_SECRET_ACCESS_KEY = 'AAAAAASECRETKEY'
AWS_REGION = 'us-east-1'

TEST_TABLE = 'python-agent-test-%s' % uuid.uuid4()


_dynamodb_scoped_metrics = [
    ('External/dynamodb.us-east-1.amazonaws.com/botocore/POST', 5),
]

_dynamodb_rollup_metrics = [
    ('External/all', 5),
    ('External/allOther', 5),
    ('External/dynamodb.us-east-1.amazonaws.com/all', 5),
    ('External/dynamodb.us-east-1.amazonaws.com/botocore/POST', 5),
]

@validate_transaction_metrics(
        'test_botocore_dynamodb:test_dynamodb',
        scoped_metrics=_dynamodb_scoped_metrics,
        rollup_metrics=_dynamodb_rollup_metrics,
        background_task=True)
@background_task()
@moto.mock_dynamodb2
def test_dynamodb():
    session = botocore.session.get_session()
    client = session.create_client(
            'dynamodb',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Create table
    resp = client.create_table(
            TableName=TEST_TABLE,
            AttributeDefinitions=[
                    {'AttributeName': 'Id', 'AttributeType': 'N'},
                    {'AttributeName': 'Foo', 'AttributeType': 'S'},
            ],
            KeySchema=[
                    {'AttributeName': 'Id', 'KeyType': 'HASH'},
                    {'AttributeName': 'Foo', 'KeyType': 'RANGE'},
            ],
            ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5,
            },
    )
    assert resp['TableDescription']['TableName'] == TEST_TABLE
    # moto response is ACTIVE, AWS response is CREATING
    # assert resp['TableDescription']['TableStatus'] == 'ACTIVE'

    # # AWS needs time to create the table
    # import time
    # time.sleep(15)

    # Put item
    resp = client.put_item(
            TableName=TEST_TABLE,
            Item={
                    'Id': {'N': '101'},
                    'Foo': {'S': 'hello_world'},
                    'SomeValue': {'S': 'some_random_attribute'},
            }
    )
    # No checking response, due to inconsistent return values.
    # moto returns resp['Attributes']. AWS returns resp['ResponseMetadata']

    # Query for item
    resp = client.query(
            TableName=TEST_TABLE,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression='#Id = :v_id',
            ExpressionAttributeNames={'#Id': 'Id'},
            ExpressionAttributeValues={':v_id': {'N': '101'}},
    )
    assert len(resp['Items']) == 1
    assert resp['Items'][0]['SomeValue']['S'] == 'some_random_attribute'

    # Delete item
    resp = client.delete_item(
            TableName=TEST_TABLE,
            Key={
                    'Id': {'N': '101'},
                    'Foo': {'S': 'hello_world'},
            },
    )
    # No checking response, due to inconsistent return values.
    # moto returns resp['Attributes']. AWS returns resp['ResponseMetadata']

    # Delete table
    resp = client.delete_table(TableName=TEST_TABLE)
    assert resp['TableDescription']['TableName'] == TEST_TABLE
    # moto response is ACTIVE, AWS response is DELETING
    # assert resp['TableDescription']['TableStatus'] == 'DELETING'
