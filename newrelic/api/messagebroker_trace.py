import functools

from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object
from newrelic.core.messagebroker_node import MessageBrokerNode


class MessageBrokerTrace(TimeTrace):

    node = MessageBrokerNode

    def __init__(self, transaction, product, target, operation,
            destination_type=None, destination_name=None):

        super(MessageBrokerTrace, self).__init__(transaction)

        if transaction:
            self.product = transaction._intern_string(product)
            self.target = transaction._intern_string(target)
            self.operation = transaction._intern_string(operation)
        else:
            self.product = product
            self.target = target
            self.operation = operation

        self.destination_type = destination_type
        self.destination_name = destination_name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
                product=self.product, target=self.target,
                operation=self.operation))

    def terminal_node(self):
        return True


def MessageBrokerTraceWrapper(wrapped, product, target, operation):

    def _nr_message_trace_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(product):
            if instance is not None:
                _product = product(instance, *args, **kwargs)
            else:
                _product = product(*args, **kwargs)
        else:
            _product = product

        if callable(target):
            if instance is not None:
                _target = target(instance, *args, **kwargs)
            else:
                _target = target(*args, **kwargs)
        else:
            _target = target

        if callable(operation):
            if instance is not None:
                _operation = operation(instance, *args, **kwargs)
            else:
                _operation = operation(*args, **kwargs)
        else:
            _operation = operation

        with MessageBrokerTrace(transaction, _product, _target, _operation):
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, _nr_message_trace_wrapper_)


def messagebroker_trace(product, target, operation):
    return functools.partial(MessageBrokerTraceWrapper, product=product,
            target=target, operation=operation)


def wrap_messagebroker_trace(module, object_path, product, target, operation):
    wrap_object(module, object_path, MessageBrokerTraceWrapper,
            (product, target, operation))
