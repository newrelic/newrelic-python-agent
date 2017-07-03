import functools

from newrelic.api.cat_header_mixin import CatHeaderMixin
from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object
from newrelic.core.messagebroker_node import MessageBrokerNode


class MessageTrace(TimeTrace, CatHeaderMixin):

    node = MessageBrokerNode
    cat_id_key = 'NewRelicID'
    cat_transaction_key = 'NewRelicTransaction'
    cat_appdata_key = 'NewRelicAppData'
    cat_synthetics_key = 'NewRelicSynthetics'

    def __init__(self, transaction, library, operation,
            destination_type, destination_name,
            params={}):

        super(MessageTrace, self).__init__(transaction)
        self.params = {}

        if transaction:
            self.library = transaction._intern_string(library)
            self.operation = transaction._intern_string(operation)
        else:
            self.library = library
            self.operation = operation

        self.destination_type = destination_type
        self.destination_name = destination_name
        self.params = params

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
                library=self.library, operation=self.operation))

    def terminal_node(self):
        return True


def MessageTraceWrapper(wrapped, library, operation, destination_type,
        destination_name, params={}):

    def _nr_message_trace_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(library):
            if instance is not None:
                _library = library(instance, *args, **kwargs)
            else:
                _library = library(*args, **kwargs)
        else:
            _library = library

        if callable(operation):
            if instance is not None:
                _operation = operation(instance, *args, **kwargs)
            else:
                _operation = operation(*args, **kwargs)
        else:
            _operation = operation

        with MessageTrace(transaction, _library, _operation,
                destination_type, destination_name, params={}):
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, _nr_message_trace_wrapper_)


def message_trace(library, operation, destination_type, destination_name,
        params={}):
    return functools.partial(MessageTraceWrapper, library=library,
            operation=operation, destination_type=destination_type,
            destination_name=destination_name, params=params)


def wrap_message_trace(module, object_path, library, operation,
        destination_type, destination_name, params={}):
    wrap_object(module, object_path, MessageTraceWrapper,
            (library, operation, destination_type, destination_name, params))
