import uuid

import botocore.session
import moto

from newrelic.agent import background_task
from testing_support.fixtures import validate_transaction_metrics


AWS_ACCESS_KEY_ID = 'AAAAAAAAAAAACCESSKEY'
AWS_SECRET_ACCESS_KEY = 'AAAAAASECRETKEY'
AWS_REGION = 'us-east-1'

TEST_BUCKET = 'python-agent-test-%s' % uuid.uuid4()


_s3_scoped_metrics = [
    ('External/s3.amazonaws.com/botocore/GET', 2),
    ('External/s3.amazonaws.com/botocore/PUT', 2),
    ('External/s3.amazonaws.com/botocore/DELETE', 2),
]

_s3_rollup_metrics = [
    ('External/all', 6),
    ('External/allOther', 6),
    ('External/s3.amazonaws.com/all', 6),
    ('External/s3.amazonaws.com/botocore/GET', 2),
    ('External/s3.amazonaws.com/botocore/PUT', 2),
    ('External/s3.amazonaws.com/botocore/DELETE', 2),
]

@validate_transaction_metrics(
        'test_botocore_s3:test_s3',
        scoped_metrics=_s3_scoped_metrics,
        rollup_metrics=_s3_rollup_metrics,
        background_task=True)
@background_task()
@moto.mock_s3
def test_s3():
    session = botocore.session.get_session()
    client = session.create_client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Create bucket
    resp = client.create_bucket(Bucket=TEST_BUCKET)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # Put object
    resp = client.put_object(
            Bucket=TEST_BUCKET,
            Key='hello_world',
            Body=b'hello_world_content'
    )
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # List bucket
    resp = client.list_objects(Bucket=TEST_BUCKET)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
    assert len(resp['Contents']) == 1
    assert resp['Contents'][0]['Key'] == 'hello_world'

    # Get object
    resp = client.get_object(Bucket=TEST_BUCKET, Key='hello_world')
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
    assert resp['Body'].read() == b'hello_world_content'

    # Delete object
    resp = client.delete_object(Bucket=TEST_BUCKET, Key='hello_world')
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 204

    # Delete bucket
    resp = client.delete_bucket(Bucket=TEST_BUCKET)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 204
