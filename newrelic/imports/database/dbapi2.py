import newrelic.agent

from newrelic.agent import (DatabaseTraceWrapper, ObjectWrapper)

class CursorWrapper(ObjectWrapper):
    def execute(self, *args, **kwargs):
        return DatabaseTraceWrapper(self.__last_object__.execute,
                (lambda sql, parameters=(): sql))(*args, **kwargs)
    def executemany(self, *args, **kwargs): 
        return DatabaseTraceWrapper(self.__last_object__.executemany,
                (lambda sql, seq_of_parameters=[]: sql))(*args, **kwargs)

class CursorFactory(ObjectWrapper):
    def __call__(self, *args, **kwargs):
        return CursorWrapper(self.__next_object__(*args, **kwargs))

class ConnectionWrapper(ObjectWrapper):
    def cursor(self, *args, **kwargs):
        return CursorFactory(self.__next_object__.cursor)(*args, **kwargs)

class ConnectionFactory(ObjectWrapper):
    def __call__(self, *args, **kwargs):
        return ConnectionWrapper(self.__next_object__(*args, **kwargs))

def instrument(module):
    module.connect = ConnectionFactory(module.connect)
