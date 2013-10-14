import types

import newrelic.core.datastore_node

import newrelic.api.transaction
import newrelic.api.time_trace
import newrelic.api.object_wrapper

class DatastoreTrace(newrelic.api.time_trace.TimeTrace):

    node = newrelic.core.datastore_node.DatastoreNode

    def __init__(self, transaction, product, target, operation):

        super(DatastoreTrace, self).__init__(transaction)

        if transaction:
            self.product = transaction._intern_string(product)
            self.target = transaction._intern_string(target)
            self.operation = transaction._intern_string(operation)
        else:
            self.product = product
            self.target = target
            self.operation = operation

    def dump(self, file):
        print >> file, self.__class__.__name__, dict(product=self.product,
                target=self.target, operation=self.operation)

    def finalize_data(self):
        settings = self.transaction.settings
        transaction_tracer = settings.transaction_tracer
        agent_limits = settings.agent_limits

    def create_node(self):
        return self.node(product=self.product, target=self.target,
                operation=self.operation, children=self.children,
                start_time=self.start_time, end_time=self.end_time,
                duration=self.duration, exclusive=self.exclusive)

    def terminal_node(self):
        return True

class DatastoreTraceWrapper(object):

    def __init__(self, wrapped, product, target, operation):
        if isinstance(wrapped, tuple):
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_product = product
        self._nr_target = target
        self._nr_operation = operation

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_product,
                              self._nr_target, self._nr_operation)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.current_transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if callable(self._nr_target):
            if self._nr_instance is not None:
                _target = self._nr_target(self._nr_instance, *args, **kwargs)
            else:
                _target = self._nr_target(*args, **kwargs)

        with DatastoreTrace(transaction, self._nr_product, _target,
                self._nr_operation):
            return self._nr_next_object(*args, **kwargs)

def datastore_trace(product, target, operation):
    def decorator(wrapped):
        return DatastoreTraceWrapper(wrapped, product, target, operation)
    return decorator

def wrap_datastore_trace(module, object_path, product, target, operation):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            DatastoreTraceWrapper, (product, target, operation))
