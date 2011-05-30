import newrelic.agent

from newrelic.agent import DatabaseTraceWrapper

class CursorWrapper(object):
    def __init__(self, cursor):
        self.__wrapped__ = cursor
    def __getattr__(self, name):
        if name == 'execute':
            return DatabaseTraceWrapper(getattr(self.__wrapped__, name),
                    (lambda sql, parameters=(): sql))
        elif name == 'executemany':
            return DatabaseTraceWrapper(getattr(self.__wrapped__, name),
                    (lambda sql, seq_of_parameters=[]: sql))
        return getattr(self.__wrapped__, name)

class CursorFactory(object):
    def __init__(self, function):
        self.__wrapped__ = function
    def __call__(self, *args, **kwargs):
        return CursorWrapper(self.__wrapped__(*args, **kwargs))

class ConnectionWrapper(object):
    def __init__(self, connection):
        self.__wrapped__ = connection
    def __getattr__(self, name):
        if name == 'cursor':
            return CursorFactory(self.__wrapped__.cursor)
        return getattr(self.__wrapped__, name)

class ConnectionFactory(object):
    def __init__(self, function):
        self.__wrapped__ = function
    def __call__(self, *args, **kwargs):
        return ConnectionWrapper(self.__wrapped__(*args, **kwargs))

def instrument(module):
    module.connect = ConnectionFactory(module.connect)
