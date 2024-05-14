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
from conftest import (  # noqa: F401, pylint: disable=W061
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

URL = "localhost:%s" % PORT
TEST_QUEUE = "python-agent-test"

_sqs_scoped_metrics = [
    ("MessageBroker/SQS/Queue/Produce/Named/%s" % TEST_QUEUE, 2),
    ("External/%s/aiobotocore/POST" % URL, 7),
]

_sqs_rollup_metrics = [
    ("MessageBroker/SQS/Queue/Produce/Named/%s" % TEST_QUEUE, 2),
    ("MessageBroker/SQS/Queue/Consume/Named/%s" % TEST_QUEUE, 1),
    ("External/all", 7),
    ("External/allOther", 7),
    ("External/%s/all" % URL, 7),
    ("External/%s/aiobotocore/POST" % URL, 7),
]


@validate_span_events(exact_agents={"aws.operation": "CreateQueue"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "ListQueues"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "SendMessage"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "ReceiveMessage"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "SendMessageBatch"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "PurgeQueue"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DeleteQueue"}, count=1)
@validate_transaction_metrics(
    "test_aiobotocore_sqs:test_aiobotocore_sqs",
    scoped_metrics=_sqs_scoped_metrics,
    rollup_metrics=_sqs_rollup_metrics,
    background_task=True,
)
@background_task()
def test_aiobotocore_sqs(loop):
    async def _test():
        async with MotoService("sqs", port=PORT):
            session = get_session()

            async with session.create_client(
                "sqs",
                region_name="us-east-1",
                endpoint_url="http://localhost:%d" % PORT,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            ) as client:

                response = await client.create_queue(QueueName=TEST_QUEUE)

                queue_url = response["QueueUrl"]

                # List queues
                response = await client.list_queues()
                for queue_name in response.get("QueueUrls", []):
                    assert queue_name

                # Send message
                resp = await client.send_message(
                    QueueUrl=queue_url,
                    MessageBody="hello_world",
                )
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

                # Receive message
                resp = await client.receive_message(
                    QueueUrl=queue_url,
                )
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

                # Send message batch
                messages = [
                    {"Id": "1", "MessageBody": "message 1"},
                    {"Id": "2", "MessageBody": "message 2"},
                    {"Id": "3", "MessageBody": "message 3"},
                ]
                resp = await client.send_message_batch(QueueUrl=queue_url, Entries=messages)
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

                # Purge queue
                resp = await client.purge_queue(QueueUrl=queue_url)
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

                # Delete queue
                resp = await client.delete_queue(QueueUrl=queue_url)
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    loop.run_until_complete(_test())
