import newrelic.agent

from newrelic.agent import DatabaseTraceWrapper

class CursorWrapper(object):
    def __init__(self, cursor):
        self.__cursor = cursor
    def __getattr__(self, name):
        if name == 'execute':
            return DatabaseTraceWrapper(getattr(self.__cursor, name),
                    (lambda sql, parameters=(): sql))
        elif name == 'executemany':
            return DatabaseTraceWrapper(getattr(self.__cursor, name),
                    (lambda sql, seq_of_parameters=[]: sql))
        return getattr(self.__cursor, name)

class CursorFactory(object):
    def __init__(self, function):
        self.__function = function
    def __call__(self, *args, **kwargs):
        return CursorWrapper(self.__function(*args, **kwargs))

class ConnectionWrapper(object):
    def __init__(self, connection):
        self.__connection = connection
    def __getattr__(self, name):
        if name == 'cursor':
            return CursorFactory(self.__connection.cursor)
        return getattr(self.__connection, name)

class ConnectionFactory(object):
    def __init__(self, function):
        self.__function = function
    def __call__(self, *args, **kwargs):
        return ConnectionWrapper(self.__function(*args, **kwargs))

def instrument(module):
    module.connect = ConnectionFactory(module.connect)
