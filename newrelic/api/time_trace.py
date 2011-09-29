import time

class TimeTrace(object):

    node = None

    def __init__(self, transaction):
        self.transaction = transaction
        self.children = []

    def __enter__(self):
        if not self.transaction:
            return

        self.start_time = time.time()
        self.transaction._push_current(self)
        return self

    def __exit__(self, exc, value, tb):
        if not self.transaction:
            return

        if self.transaction.stopped:
            self.end_time = self.transaction.end_time
        else:
            self.end_time = time.time()

        self.duration = self.end_time - self.start_time
        self.duration = max(0, self.duration)

        self.exclusive = self.duration
        for child in self.children:
            self.exclusive -= child.duration
        self.exclusive = max(0, self.exclusive)
        self.exclusive = min(self.exclusive, self.duration)

        parent = self.transaction._pop_current(self)

        self.finalize()

        if self.node:
            node = self.node(**dict((k, self.__dict__[k])
                    for k in self.node._fields))
            self.transaction._process_node(node)
            parent.children.append(node)

        self.transaction = None
        self.children = []

    def finalize(self):
        pass
