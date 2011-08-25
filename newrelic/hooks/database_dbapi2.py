import newrelic.api.database_trace
import newrelic.api.function_trace
import newrelic.api.external_trace

def instrument(module):

    class CursorWrapper(object):
        def __init__(self, cursor):
            self.__cursor = cursor
        def execute(self, *args, **kwargs):
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                    self.__cursor.execute,
                    (lambda sql, parameters=(): sql),
                    module)(*args, **kwargs)
        def executemany(self, *args, **kwargs): 
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                    self.__cursor.executemany,
                    (lambda sql, seq_of_parameters=[]: sql),
                    module)(*args, **kwargs)
        def __getattr__(self, name):
            return getattr(self.__cursor, name)

    class ConnectionWrapper(object):
        def __init__(self, connection):
            self.__connection = connection
        def cursor(self, *args, **kwargs):
            return CursorWrapper(self.__connection.cursor(*args, **kwargs))
        def commit(self, *args, **kwargs):
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                self.__connection.commit, 'COMMIT',
                module)(*args, **kwargs)
        def rollback(self, *args, **kwargs):
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                self.__connection.rollback, 'ROLLBACK',
                module)(*args, **kwargs)
        def __getattr__(self, name):
            return getattr(self.__connection, name)

    class ConnectionFactory(object):
        def __init__(self, connect):
            self.__connect = connect
        def __call__(self, *args, **kwargs):
            return ConnectionWrapper(self.__connect(*args, **kwargs))

    newrelic.api.function_trace.wrap_function_trace(module, 'connect',
            name='%s:%s' % (module.__name__, 'connect'))

    module.connect = ConnectionFactory(module.connect)
