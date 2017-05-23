import uuid

import botocore.session
import moto

from newrelic.agent import background_task
from testing_support.fixtures import validate_transaction_metrics

AWS_ACCESS_KEY_ID = 'AAAAAAAAAAAACCESSKEY'
AWS_SECRET_ACCESS_KEY = 'AAAAAASECRETKEY'
AWS_REGION = 'us-east-1'

TEST_QUEUE = 'python-agent-test-%s' % uuid.uuid4()


_sqs_scoped_metrics = [
    ('External/queue.amazonaws.com/botocore/POST', 6),
]

_sqs_rollup_metrics = [
    ('External/all', 6),
    ('External/allOther', 6),
    ('External/queue.amazonaws.com/all', 6),
    ('External/queue.amazonaws.com/botocore/POST', 6),
]

@validate_transaction_metrics(
        'test_botocore_sqs:test_sqs',
        scoped_metrics=_sqs_scoped_metrics,
        rollup_metrics=_sqs_rollup_metrics,
        background_task=True)
@background_task()
@moto.mock_sqs
def test_sqs():
    session = botocore.session.get_session()
    client = session.create_client(
            'sqs',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Create queue
    resp = client.create_queue(QueueName=TEST_QUEUE)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # QueueUrl is needed for rest of methods.
    QUEUE_URL = resp['QueueUrl']

    # Send message
    resp = client.send_message(QueueUrl=QUEUE_URL, MessageBody='hello_world')
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # Receive message
    resp = client.receive_message(QueueUrl=QUEUE_URL)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # Send message batch
    messages = [
        {'Id': '1', 'MessageBody': 'message 1'},
        {'Id': '2', 'MessageBody': 'message 2'},
        {'Id': '3', 'MessageBody': 'message 3'},
    ]
    resp = client.send_message_batch(QueueUrl=QUEUE_URL, Entries=messages)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # Purge queue
    resp = client.purge_queue(QueueUrl=QUEUE_URL)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # Delete queue
    resp = client.delete_queue(QueueUrl=QUEUE_URL)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
