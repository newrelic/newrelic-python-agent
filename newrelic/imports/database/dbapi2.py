import newrelic.agent

from newrelic.agent import (DatabaseTraceWrapper, ObjectWrapper)

class CursorWrapper(ObjectWrapper):
    def __getattr__(self, name):
        if name == 'execute':
            return DatabaseTraceWrapper(getattr(self.__last_object__, name),
                    (lambda sql, parameters=(): sql))
        elif name == 'executemany':
            return DatabaseTraceWrapper(getattr(self.__last_object__, name),
                    (lambda sql, seq_of_parameters=[]: sql))
        return getattr(self.__last_object__, name)

class CursorFactory(ObjectWrapper):
    def __call__(self, *args, **kwargs):
        return CursorWrapper(self.__next_object__(*args, **kwargs))

class ConnectionWrapper(ObjectWrapper):
    def __getattr__(self, name):
        if name == 'cursor':
            return CursorFactory(self.__last_object__.cursor)
        return getattr(self.__last_object__, name)

class ConnectionFactory(ObjectWrapper):
    def __call__(self, *args, **kwargs):
        return ConnectionWrapper(self.__next_object__(*args, **kwargs))

def instrument(module):
    module.connect = ConnectionFactory(module.connect)
