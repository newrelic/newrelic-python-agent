import time

class TimeTrace(object):

    node = None

    def __init__(self, transaction):
        self.transaction = transaction
        self.children = []
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0
        self.exclusive = 0.0

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

        return self

    def __exit__(self, exc, value, tb):
        if not self.transaction:
            return

        # If recording of time for transaction has already been
        # stopped, then that time has to be used.

        if self.transaction.stopped:
            self.end_time = self.transaction.end_time
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

        parent = self.transaction._pop_current(self)

        # Give chance for derived class to finalize any data in
        # this object instance.

        self.finalize_data(exc, value, tb)

        # Give chance for derived class to create a standin node
        # object to be used in the transaction trace. If we get
        # one then give chance for transaction object to do
        # something with it, as well as our parent node.

        node = self.create_node()

        if node:
            self.transaction._process_node(node)
            parent.process_child(node)

        # Wipe out transaction reference so can't use object again.

        self.transaction = None

    def finalize_data(self, exc=None, value=None, tb=None):
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
