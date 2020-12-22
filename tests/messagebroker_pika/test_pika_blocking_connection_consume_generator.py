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

import pika

from newrelic.api.background_task import background_task

from conftest import QUEUE, EXCHANGE, CORRELATION_ID, REPLY_TO, HEADERS, BODY
from testing_support.fixtures import (validate_transaction_metrics,
        validate_tt_collector_json)
from testing_support.db_settings import rabbitmq_settings

DB_SETTINGS = rabbitmq_settings()[0]

_message_broker_tt_params = {
    'queue_name': QUEUE,
    'routing_key': QUEUE,
    'correlation_id': CORRELATION_ID,
    'reply_to': REPLY_TO,
    'headers': HEADERS.copy(),
}

_test_blocking_connection_consume_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/%s' % EXCHANGE, None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/%s' % EXCHANGE, None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Unknown', None),
]


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_break'),
        scoped_metrics=_test_blocking_connection_consume_metrics,
        rollup_metrics=_test_blocking_connection_consume_metrics,
        background_task=True)
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
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
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
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
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
@background_task()
def test_blocking_connection_consume_timeout(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        for result in channel.consume(QUEUE, inactivity_timeout=0.01):
            # result is None if there is a timeout
            if result and any(result):
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
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
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
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
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
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/%s' % EXCHANGE, None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Unknown', None),
]


@validate_transaction_metrics(
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_many'),
        scoped_metrics=_test_blocking_connection_consume_many_metrics,
        rollup_metrics=_test_blocking_connection_consume_many_metrics,
        background_task=True)
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
@background_task()
def test_blocking_connection_consume_many(produce_five):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        consumed = 0
        for result in channel.consume(QUEUE, inactivity_timeout=0.01):
            if result and any(result):
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
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
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
        assert result is None or not any(result)

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
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
def test_blocking_connection_consume_outside_txn(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        consumer = channel.consume(QUEUE)

        try:
            for method_frame, properties, body in consumer:
                assert hasattr(method_frame, '_nr_start_time')
                assert body == BODY
                break
        finally:
            # Required for PyPy compatibility, see http://pypy.org/compat.html
            consumer.close()


def test_blocking_connection_consume_many_outside_txn(produce_five):

    @validate_transaction_metrics(
            'Named/%s' % EXCHANGE,
            scoped_metrics=_test_blocking_connection_consume_metrics,
            rollup_metrics=_test_blocking_connection_consume_metrics,
            background_task=True,
            group='Message/RabbitMQ/Exchange')
    @validate_tt_collector_json(
            message_broker_params=_message_broker_tt_params)
    def consume_it(consumer, up_next=None):
        if up_next is None:
            method_frame, properties, body = next(consumer)
        else:
            method_frame, properties, body = up_next
        assert hasattr(method_frame, '_nr_start_time')
        assert body == BODY
        return next(consumer)

    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        consumer = channel.consume(QUEUE)

        up_next = None
        for i in range(6):
            try:
                up_next = consume_it(consumer, up_next=up_next)
            except StopIteration:
                pass
            finally:
                consumer.close()


@validate_transaction_metrics(
        'Named/%s' % EXCHANGE,
        scoped_metrics=_test_blocking_connection_consume_metrics,
        rollup_metrics=_test_blocking_connection_consume_metrics,
        background_task=True,
        group='Message/RabbitMQ/Exchange')
@validate_tt_collector_json(message_broker_params=_message_broker_tt_params)
def test_blocking_connection_consume_using_methods_outside_txn(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        consumer = channel.consume(QUEUE, inactivity_timeout=0.01)

        method, properties, body = next(consumer)
        assert hasattr(method, '_nr_start_time')
        assert body == BODY

        result = next(consumer)
        assert result is None or not any(result)

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
        ('test_pika_blocking_connection_consume_generator:'
                'test_blocking_connection_consume_exception_on_creation'),
        scoped_metrics=_test_blocking_connection_consume_empty_metrics,
        rollup_metrics=_test_blocking_connection_consume_empty_metrics,
        background_task=True)
@background_task()
def test_blocking_connection_consume_exception_on_creation():
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        try:
            channel.consume(kittens=True)
        except TypeError:
            # this is expected
            pass
        else:
            # this is not
            assert False, 'TypeError was not raised'
