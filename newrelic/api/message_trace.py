import functools

from newrelic.common.coroutine import async_proxy, TraceContext
from newrelic.api.cat_header_mixin import CatHeaderMixin
from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object
from newrelic.core.message_node import MessageNode


class MessageTrace(TimeTrace, CatHeaderMixin):

    cat_id_key = 'NewRelicID'
    cat_transaction_key = 'NewRelicTransaction'
    cat_appdata_key = 'NewRelicAppData'
    cat_synthetics_key = 'NewRelicSynthetics'

    def __init__(self, transaction, library, operation,
            destination_type, destination_name,
            params=None):

        super(MessageTrace, self).__init__(transaction)

        self.settings = self.transaction and self.transaction.settings or None

        if self.transaction:
            self.library = self.transaction._intern_string(library)
            self.operation = self.transaction._intern_string(operation)

        else:
            self.library = library
            self.operation = operation

        # Only record parameters when not high security mode and only
        # when enabled in settings.

        if (self.should_record_segment_params and self.settings and
                self.settings.message_tracer.segment_parameters_enabled):
            self.params = params
        else:
            self.params = None

        self.destination_type = destination_type
        self.destination_name = destination_name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
                library=self.library, operation=self.operation))

    def terminal_node(self):
        return True

    def create_node(self):
        return MessageNode(
                library=self.library,
                operation=self.operation,
                children=self.children,
                start_time=self.start_time,
                end_time=self.end_time,
                duration=self.duration,
                exclusive=self.exclusive,
                destination_name=self.destination_name,
                destination_type=self.destination_type,
                params=self.params,
                is_async=self.is_async,
                guid=self.guid,
                agent_attributes=self.agent_attributes)


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

        if callable(destination_type):
            if instance is not None:
                _destination_type = destination_type(instance, *args, **kwargs)
            else:
                _destination_type = destination_type(*args, **kwargs)
        else:
            _destination_type = destination_type

        if callable(destination_name):
            if instance is not None:
                _destination_name = destination_name(instance, *args, **kwargs)
            else:
                _destination_name = destination_name(*args, **kwargs)
        else:
            _destination_name = destination_name

        trace = MessageTrace(transaction, _library, _operation,
                _destination_type, _destination_name, params={})

        proxy = async_proxy(wrapped)
        if proxy:
            return proxy(wrapped(*args, **kwargs), TraceContext(trace))

        with trace:
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
