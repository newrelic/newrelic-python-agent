import pika

from newrelic.api.background_task import background_task

from testing_support.settings import rabbitmq_settings
from testing_support.fixtures import (override_application_settings,
        validate_transaction_metrics)

DB_SETTINGS = rabbitmq_settings()

ENCODING_KEY = '1234567890123456789012345678901234567890'
_override_settings = {
    'cross_process_id': '1#1',
    'encoding_key': ENCODING_KEY,
    'trusted_account_ids': [1],
    'browser_monitoring.enabled': False,
}


@background_task()
def do_basic_publish(channel, QUEUE):
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE,
        body='Testing CAT 123',
    )


_test_cat_basic_get_scoped_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', 1),
]
_test_cat_basic_get_rollup_metrics = list(_test_cat_basic_get_scoped_metrics)
_test_cat_basic_get_rollup_metrics.append(('ClientApplication/1#1/all', 1))


@validate_transaction_metrics(
        'test_cat:do_basic_get',
        scoped_metrics=_test_cat_basic_get_scoped_metrics,
        rollup_metrics=_test_cat_basic_get_rollup_metrics,
        background_task=True)
@background_task()
def do_basic_get(channel, QUEUE):
    _, properties, msg = channel.basic_get(QUEUE)

    headers = properties.headers
    assert headers
    assert 'NewRelicID' in headers
    assert 'NewRelicTransaction' in headers
    assert msg == b'Testing CAT 123'


@override_application_settings(_override_settings)
def test_basic_get_cat_headers():
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        channel.queue_declare('TESTCAT', durable=False)

        try:
            do_basic_publish(channel, 'TESTCAT')
            do_basic_get(channel, 'TESTCAT')

        finally:
            channel.queue_delete('TESTCAT')
