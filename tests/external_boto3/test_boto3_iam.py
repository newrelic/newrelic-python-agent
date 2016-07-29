import uuid

import boto3
import moto

from newrelic.agent import background_task
from testing_support.fixtures import validate_transaction_metrics

TEST_USER = 'python-agent-test-%s' % uuid.uuid4()
TEST_GROUP = 'python-agent-test-%s' % uuid.uuid4()

_iam_scoped_metrics = [
    ('External/iam.amazonaws.com/botocore/POST', 6),
]

_iam_rollup_metrics = [
    ('External/all', 6),
    ('External/allOther', 6),
    ('External/iam.amazonaws.com/all', 6),
    ('External/iam.amazonaws.com/botocore/POST', 6),
]

@validate_transaction_metrics(
        'test_boto3_iam:test_iam',
        scoped_metrics=_iam_scoped_metrics,
        rollup_metrics=_iam_rollup_metrics,
        background_task=True)
@background_task()
@moto.mock_iam
def test_iam():
    iam = boto3.client('iam')

    # Create user
    resp = iam.create_user(UserName=TEST_USER)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # Create a group
    resp = iam.create_group(GroupName=TEST_GROUP)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # Add the user to the group
    resp = iam.add_user_to_group(UserName=TEST_USER, GroupName=TEST_GROUP)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # Get the user
    resp = iam.get_user(UserName=TEST_USER)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
    assert resp['User']['UserName'] == TEST_USER

    # Get the group
    resp = iam.get_group(GroupName=TEST_GROUP)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
    assert resp['Group']['GroupName'] == TEST_GROUP

    # Delete the user
    resp = iam.delete_user(UserName=TEST_USER)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
