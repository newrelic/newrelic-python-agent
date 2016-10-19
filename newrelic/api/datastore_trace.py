import functools

from .time_trace import TimeTrace
from .transaction import current_transaction
from ..core.datastore_node import DatastoreNode
from ..common.object_wrapper import FunctionWrapper, wrap_object

class DatastoreTrace(TimeTrace):

    def __init__(self, transaction, product, target, operation,
            host=None, port_path_or_id=None, database_name=None):

        super(DatastoreTrace, self).__init__(transaction)

        if transaction:
            self.product = transaction._intern_string(product)
            self.target = transaction._intern_string(target)
            self.operation = transaction._intern_string(operation)
        else:
            self.product = product
            self.target = target
            self.operation = operation

        self.host = host
        self.port_path_or_id = port_path_or_id
        self.database_name = database_name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
                product=self.product, target=self.target,
                operation=self.operation))

    def create_node(self):
        return DatastoreNode(product=self.product, target=self.target,
                operation=self.operation, children=self.children,
                start_time=self.start_time, end_time=self.end_time,
                duration=self.duration, exclusive=self.exclusive,
                host=self.host, port_path_or_id=self.port_path_or_id,
                database_name=self.database_name)

    def terminal_node(self):
        return True

def DatastoreTraceWrapper(wrapped, product, target, operation):

    def _nr_datastore_trace_wrapper_(wrapped, instance, args, kwargs):
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

        with DatastoreTrace(transaction, _product, _target, _operation):
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, _nr_datastore_trace_wrapper_)

def datastore_trace(product, target, operation):
    return functools.partial(DatastoreTraceWrapper, product=product,
            target=target, operation=operation)

def wrap_datastore_trace(module, object_path, product, target, operation):
    wrap_object(module, object_path, DatastoreTraceWrapper,
            (product, target, operation))
