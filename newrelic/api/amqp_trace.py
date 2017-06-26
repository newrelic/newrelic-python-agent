import functools

from newrelic.api.messagebroker_trace import MessageBrokerTrace
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object
from newrelic.api.transaction import current_transaction


class AmqpTrace(MessageBrokerTrace):
    def __init__(self, transaction, library, operation,
            destination_name, message_properties=None, routing_key=None,
            reply_to=None, correlation_id=None, queue_name=None,
            exchange_type=None, subscribed=False, headers=None):

        super(AmqpTrace, self).__init__(transaction=transaction,
                library=library,
                operation=operation,
                destination_type='Exchange',
                destination_name=destination_name,
                message_properties=message_properties,
                params={})

        if routing_key is not None:
            self.params['routing_key'] = routing_key

        if reply_to is not None:
            self.params['reply_to'] = reply_to

        if correlation_id is not None:
            self.params['correlation_id'] = correlation_id

        if exchange_type is not None:
            self.params['exchange_type'] = exchange_type

        if operation.lower() == 'consume' and queue_name is not None:
            self.params['queue_name'] = queue_name

        if headers is not None:
            self.params['headers'] = headers

        # Add routing key to agent attributes if subscribed
        if subscribed and routing_key is not None:
            transaction._request_environment['ROUTING_KEY'] = routing_key


def AmqpTraceWrapper(wrapped, library, operation,
            destination_name, message_properties=None, routing_key=None,
            reply_to=None, correlation_id=None, queue_name=None,
            exchange_type=None, subscribed=False):

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        with AmqpTrace(transaction=transaction,
                library=library,
                operation=operation,
                destination_name=destination_name,
                message_properties=message_properties,
                routing_key=routing_key,
                reply_to=reply_to,
                correlation_id=correlation_id,
                queue_name=queue_name,
                exchange_type=exchange_type,
                subscribed=subscribed):
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, wrapper)


def amqp_trace(library, operation,
            destination_name, message_properties=None, routing_key=None,
            reply_to=None, correlation_id=None, queue_name=None,
            exchange_type=None, subscribed=False):
    return functools.partial(AmqpTraceWrapper, library=library,
            operation=operation, destination_name=destination_name,
            message_properties=message_properties, routing_key=routing_key,
            reply_to=reply_to, correlation_id=correlation_id,
            queue_name=queue_name, exchange_type=exchange_type,
            subscribed=subscribed)


def wrap_amqp_trace(module, object_path, library, operation,
            destination_name, message_properties=None, routing_key=None,
            reply_to=None, correlation_id=None, queue_name=None,
            exchange_type=None, subscribed=False):
    wrap_object(module, object_path, AmqpTraceWrapper,
            (library, operation, destination_name, message_properties,
            routing_key, reply_to, correlation_id, queue_name, exchange_type,
            subscribed))
