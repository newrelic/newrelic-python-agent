import time
import traceback
import logging

_logger = logging.getLogger(__name__)

class TimeTrace(object):

    node = None

    def __init__(self, transaction):
        self.transaction = transaction
        self.children = []
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0
        self.exclusive = 0.0
        self.activated = False

        # Don't do further tracing of transaction if
        # it has been explicitly stopped.

        if transaction and transaction.stopped:
            self.transaction = None

    def __enter__(self):
        if not self.transaction:
            return self

        # Don't do any tracing if parent is designated
        # as a terminal node.

        parent = self.transaction.active_node()

        if not parent or parent.terminal_node():
            self.transaction = None
            return parent

        # Record start time.

        self.start_time = time.time()

        # Push ourselves as the current node.

        self.transaction._push_current(self)

        self.activated = True

        return self

    def __exit__(self, exc, value, tb):
        if not self.transaction:
            return

        # Check for violation of context manager protocol where
        # __exit__() is called before __enter__().

        if not self.activated:
            _logger.error('Runtime instrumentation error. The __exit__() '
                    'method of %r was called prior to __enter__() being '
                    'called. Report this issue to New Relic support.\n%s',
                    self, ''.join(traceback.format_stack()[:-1]))

            return

        # Wipe out transaction reference so can't use object
        # again. Retain reference as local variable for use in
        # this call though.

        transaction = self.transaction

        self.transaction = None

        # If recording of time for transaction has already been
        # stopped, then that time has to be used.

        if transaction.stopped:
            self.end_time = transaction.end_time
        else:
            self.end_time = time.time()

        # Ensure end time is greater. Should be unless the
        # system clock has been updated.

        if self.end_time < self.start_time:
            self.end_time = self.start_time

        # Calculate duration and exclusive time. Up till now the
        # exclusive time value had been used to accumulate
        # duration from child nodes as negative value, so just
        # add duration to that to get our own exclusive time.

        self.duration = self.end_time - self.start_time

        self.exclusive += self.duration

        if self.exclusive < 0:
            self.exclusive = 0

        # Pop ourselves as current node. The return value is our
        # parent.

        parent = transaction._pop_current(self)

        # Give chance for derived class to finalize any data in
        # this object instance. The transaction is passed as a
        # parameter since the transaction object on this instance
        # will have been cleared above.

        self.finalize_data(transaction, exc, value, tb)

        # Give chance for derived class to create a standin node
        # object to be used in the transaction trace. If we get
        # one then give chance for transaction object to do
        # something with it, as well as our parent node.

        node = self.create_node()

        if node:
            transaction._process_node(node)
            parent.process_child(node)

    def finalize_data(self, transaction, exc=None, value=None, tb=None):
        pass

    def create_node(self):
        if self.node:
            return self.node(**dict((k, self.__dict__[k])
                    for k in self.node._fields))
        return self

    def terminal_node(self):
        return False

    def process_child(self, node):
        self.children.append(node)
        self.exclusive -= node.duration
