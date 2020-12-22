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
import pytest

import botocore.session
import moto

from newrelic.api.background_task import background_task
from testing_support.fixtures import (validate_transaction_metrics,
        override_application_settings)
from testing_support.validators.validate_span_events import (
        validate_span_events)

MOTO_VERSION = tuple(int(v) for v in moto.__version__.split('.')[:3])

# patch earlier versions of moto to support py37
if sys.version_info >= (3, 7) and MOTO_VERSION <= (1, 3, 1):
    import re
    moto.packages.responses.responses.re._pattern_type = re.Pattern

AWS_ACCESS_KEY_ID = 'AAAAAAAAAAAACCESSKEY'
AWS_SECRET_ACCESS_KEY = 'AAAAAASECRETKEY'
AWS_REGION = 'us-east-1'

TEST_QUEUE = 'python-agent-test-%s' % uuid.uuid4()


_sqs_scoped_metrics = [
    ('MessageBroker/SQS/Queue/Produce/Named/%s'
        % TEST_QUEUE, 2),
    ('External/queue.amazonaws.com/botocore/POST', 3),
]

_sqs_rollup_metrics = [
    ('MessageBroker/SQS/Queue/Produce/Named/%s'
        % TEST_QUEUE, 2),
    ('MessageBroker/SQS/Queue/Consume/Named/%s'
        % TEST_QUEUE, 1),
    ('External/all', 3),
    ('External/allOther', 3),
    ('External/queue.amazonaws.com/all', 3),
    ('External/queue.amazonaws.com/botocore/POST', 3),
]

_sqs_scoped_metrics_malformed = [
    ('MessageBroker/SQS/Queue/Produce/Named/Unknown', 1),
]

_sqs_rollup_metrics_malformed = [
    ('MessageBroker/SQS/Queue/Produce/Named/Unknown', 1),
]


@override_application_settings({'distributed_tracing.enabled': True})
@validate_span_events(exact_agents={'aws.operation': 'CreateQueue'}, count=1)
@validate_span_events(exact_agents={'aws.operation': 'SendMessage'}, count=1)
@validate_span_events(
        exact_agents={'aws.operation': 'ReceiveMessage'}, count=1)
@validate_span_events(
        exact_agents={'aws.operation': 'SendMessageBatch'}, count=1)
@validate_span_events(exact_agents={'aws.operation': 'PurgeQueue'}, count=1)
@validate_span_events(exact_agents={'aws.operation': 'DeleteQueue'}, count=1)
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


@override_application_settings({'distributed_tracing.enabled': True})
@validate_transaction_metrics(
        'test_botocore_sqs:test_sqs_malformed',
        scoped_metrics=_sqs_scoped_metrics_malformed,
        rollup_metrics=_sqs_rollup_metrics_malformed,
        background_task=True)
@background_task()
@moto.mock_sqs
def test_sqs_malformed():
    session = botocore.session.get_session()
    client = session.create_client(
            'sqs',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Malformed send message, uses arg instead of kwarg
    with pytest.raises(TypeError):
        client.send_message('https://fake-url/', MessageBody='hello_world')
