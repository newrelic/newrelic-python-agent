import sys
import boto3
import moto
import pytest

from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics

MOTO_VERSION = tuple(int(v) for v in moto.__version__.split('.'))

# patch earlier versions of moto to support py37
if sys.version_info >= (3, 7) and MOTO_VERSION <= (1, 3, 1):
    import re
    moto.packages.responses.responses.re._pattern_type = re.Pattern

AWS_ACCESS_KEY_ID = 'AAAAAAAAAAAACCESSKEY'
AWS_SECRET_ACCESS_KEY = 'AAAAAASECRETKEY'
AWS_REGION_NAME = 'us-east-1'
SNS_URL = 'sns-us-east-1.amazonaws.com'
TOPIC = 'arn:aws:sns:us-east-1:123456789012:some-topic'
sns_metrics = [
        ('MessageBroker/SimpleNotificationService/Topic'
        '/Produce/Named/%s' % TOPIC, 1)]
sns_metrics_phone = [
        ('MessageBroker/SimpleNotificationService/Topic'
        '/Produce/Named/PhoneNumber', 1)]


@pytest.mark.parametrize('topic_argument', ('TopicArn', 'TargetArn'))
@validate_transaction_metrics('test_boto3_sns:test_publish_to_sns_topic',
        scoped_metrics=sns_metrics, rollup_metrics=sns_metrics,
        background_task=True)
@background_task()
@moto.mock_sns
def test_publish_to_sns_topic(topic_argument):
    conn = boto3.client('sns',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME)

    topic_arn = conn.create_topic(Name='some-topic')['TopicArn']

    kwargs = {topic_argument: topic_arn}
    published_message = conn.publish(Message='my msg', **kwargs)
    assert 'MessageId' in published_message


@validate_transaction_metrics('test_boto3_sns:test_publish_to_sns_phone',
        scoped_metrics=sns_metrics_phone, rollup_metrics=sns_metrics_phone,
        background_task=True)
@background_task()
@moto.mock_sns
def test_publish_to_sns_phone():
    conn = boto3.client('sns',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME)

    topic_arn = conn.create_topic(Name='some-topic')['TopicArn']
    conn.subscribe(TopicArn=topic_arn, Protocol='sms', Endpoint='5555555555')

    published_message = conn.publish(
            PhoneNumber='5555555555', Message='my msg')
    assert 'MessageId' in published_message
