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

TOPIC = "arn:aws:sns:us-east-1:123456789012:some-topic"
sns_metrics = [
    (f"MessageBroker/SNS/Topic/Produce/Named/{TOPIC}", 1),
    ("MessageBroker/SNS/Topic/Produce/Named/PhoneNumber", 1),
]


@validate_span_events(expected_agents=("aws.requestId",), count=4)
@validate_span_events(exact_agents={"aws.operation": "CreateTopic"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "Publish"}, count=2)
@validate_transaction_metrics(
    "test_aiobotocore_sns:test_publish_to_sns",
    scoped_metrics=sns_metrics,
    rollup_metrics=sns_metrics,
    background_task=True,
)
@background_task()
def test_publish_to_sns(loop):
    async def _test():
        async with MotoService("sns", port=PORT):
            session = get_session()

            async with session.create_client(
                "sns",
                region_name="us-east-1",
                endpoint_url=f"http://localhost:{PORT}",
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            ) as client:
                topic_arn = await client.create_topic(Name="some-topic")
                topic_arn_name = topic_arn["TopicArn"]

                kwargs = {"TopicArn": topic_arn_name}
                published_message = await client.publish(Message="my message", **kwargs)
                assert "MessageId" in published_message

                await client.subscribe(TopicArn=topic_arn_name, Protocol="sms", Endpoint="5555555555")

                published_message = await client.publish(PhoneNumber="5555555555", Message="my msg")
                assert "MessageId" in published_message

    loop.run_until_complete(_test())
