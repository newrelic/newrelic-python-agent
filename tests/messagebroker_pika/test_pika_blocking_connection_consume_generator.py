import pika

from newrelic.api.background_task import background_task
from newrelic.api.transaction import end_of_transaction

from conftest import QUEUE, EXCHANGE, BODY
from testing_support.fixtures import validate_transaction_metrics
from testing_support.settings import rabbitmq_settings

DB_SETTINGS = rabbitmq_settings()


_test_blocking_connection_consume_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/%s' % EXCHANGE, None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/%s' % EXCHANGE, 1),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Unknown', None),
]


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_break'),
        scoped_metrics=_test_blocking_connection_consume_metrics,
        rollup_metrics=_test_blocking_connection_consume_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume_break(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        for method_frame, properties, body in channel.consume(QUEUE):
            assert hasattr(method_frame, '_nr_start_time')
            assert body == BODY
            break


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_connection_close'),
        scoped_metrics=_test_blocking_connection_consume_metrics,
        rollup_metrics=_test_blocking_connection_consume_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume_connection_close(producer):
    connection = pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host']))
    channel = connection.channel()

    try:
        for method_frame, properties, body in channel.consume(QUEUE):
            assert hasattr(method_frame, '_nr_start_time')
            assert body == BODY
            channel.close()
            connection.close()
    except pika.exceptions.ConnectionClosed:
        pass
    except:
        connection.close()


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_timeout'),
        scoped_metrics=_test_blocking_connection_consume_metrics,
        rollup_metrics=_test_blocking_connection_consume_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume_timeout(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        for result in channel.consume(QUEUE, inactivity_timeout=0.01):
            # result is None if there is a timeout
            if result:
                method_frame, properties, body = result
                channel.basic_ack(method_frame.delivery_tag)
                assert hasattr(method_frame, '_nr_start_time')
                assert body == BODY
            else:
                # timeout hit!
                break


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_exception_in_for_loop'),
        scoped_metrics=_test_blocking_connection_consume_metrics,
        rollup_metrics=_test_blocking_connection_consume_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume_exception_in_for_loop(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        try:
            # We should still create the metric in this case even if there is
            # an exception
            for result in channel.consume(QUEUE):
                1 / 0
        except ZeroDivisionError:
            # Expected error
            pass
        except Exception as e:
            assert False, 'Wrong exception was raised: %s' % e
        else:
            assert False, 'No exception was raised!'


_test_blocking_connection_consume_empty_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/%s' % EXCHANGE, None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/%s' % EXCHANGE, None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Unknown', None),
]


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_exception_in_generator'),
        scoped_metrics=_test_blocking_connection_consume_empty_metrics,
        rollup_metrics=_test_blocking_connection_consume_empty_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume_exception_in_generator():
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        try:
            # Since the pytest fixture is not used, the QUEUE will not exist
            for result in channel.consume(QUEUE):
                pass
        except pika.exceptions.ChannelClosed:
            # Expected error
            pass
        except Exception as e:
            assert False, 'Wrong exception was raised: %s' % e
        else:
            assert False, 'No exception was raised!'


_test_blocking_connection_consume_many_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/%s' % EXCHANGE, None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/%s' % EXCHANGE, 5),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Unknown', None),
]


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_many'),
        scoped_metrics=_test_blocking_connection_consume_many_metrics,
        rollup_metrics=_test_blocking_connection_consume_many_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume_many(produce_five):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        consumed = 0
        for result in channel.consume(QUEUE, inactivity_timeout=0.01):
            if result:
                consumed += 1
            else:
                assert consumed == 5
                break


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_using_methods'),
        scoped_metrics=_test_blocking_connection_consume_metrics,
        rollup_metrics=_test_blocking_connection_consume_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume_using_methods(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        consumer = channel.consume(QUEUE, inactivity_timeout=0.01)

        method, properties, body = next(consumer)
        assert hasattr(method, '_nr_start_time')
        assert body == BODY

        result = next(consumer)
        assert result is None

        try:
            consumer.throw(ZeroDivisionError)
        except ZeroDivisionError:
            # This is expected
            pass
        else:
            # this is not
            assert False, 'No exception was raised!'

        result = consumer.close()
        assert result is None


@validate_transaction_metrics(
        'Named/%s' % EXCHANGE,
        scoped_metrics=_test_blocking_connection_consume_metrics,
        rollup_metrics=_test_blocking_connection_consume_metrics,
        background_task=True,
        group='Message/RabbitMQ/Exchange')
def test_blocking_connection_consume_outside_txn(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        for method_frame, properties, body in channel.consume(QUEUE):
            assert hasattr(method_frame, '_nr_start_time')
            assert body == BODY
            break


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_ending_txn'),
        scoped_metrics=_test_blocking_connection_consume_metrics,
        rollup_metrics=_test_blocking_connection_consume_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume_ending_txn(produce_five):

    # Despite consuming 5 messages from the queue, only 1 gets a metric because
    # end_of_transaction is called.

    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        consumed = 0
        for result in channel.consume(QUEUE, inactivity_timeout=0.01):
            if result:
                consumed += 1
                end_of_transaction()
                method_frame, properties, body = result
                assert hasattr(method_frame, '_nr_start_time')
                assert body == BODY
            else:
                assert consumed == 5
                break
