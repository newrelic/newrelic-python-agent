import newrelic.agent

from newrelic.agent import (DatabaseTraceWrapper, ObjectWrapper)

class CursorWrapper(ObjectWrapper):
    def __getattr__(self, name):
        if name == 'execute':
            return DatabaseTraceWrapper(getattr(self.wrapped, name),
                    (lambda sql, parameters=(): sql))
        elif name == 'executemany':
            return DatabaseTraceWrapper(getattr(self.wrapped, name),
                    (lambda sql, seq_of_parameters=[]: sql))
        return getattr(self.wrapped, name)

class CursorFactory(ObjectWrapper):
    def __call__(self, *args, **kwargs):
        return CursorWrapper(self.wrapped(*args, **kwargs))

class ConnectionWrapper(ObjectWrapper):
    def __getattr__(self, name):
        if name == 'cursor':
            return CursorFactory(self.wrapped.cursor)
        return getattr(self.wrapped, name)

class ConnectionFactory(ObjectWrapper):
    def __call__(self, *args, **kwargs):
        return ConnectionWrapper(self.wrapped(*args, **kwargs))

def instrument(module):
    module.connect = ConnectionFactory(module.connect)
