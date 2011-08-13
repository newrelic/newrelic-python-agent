import newrelic.api.object_wrapper
import newrelic.api.database_trace
import newrelic.api.function_trace
import newrelic.api.external_trace

def instrument(module):

    class CursorWrapper(newrelic.api.object_wrapper.ObjectWrapper):
        def execute(self, *args, **kwargs):
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                    self.__last_object__.execute,
                    (lambda sql, parameters=(): sql))(*args, **kwargs)
        def executemany(self, *args, **kwargs): 
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                    self.__last_object__.executemany,
                    (lambda sql, seq_of_parameters=[]: sql))(*args, **kwargs)

    class CursorFactory(newrelic.api.object_wrapper.ObjectWrapper):
        def __call__(self, *args, **kwargs):
            return CursorWrapper(self.__next_object__(*args, **kwargs))

    class ConnectionWrapper(newrelic.api.object_wrapper.ObjectWrapper):
        def cursor(self, *args, **kwargs):
            return CursorFactory(self.__next_object__.cursor)(*args, **kwargs)
        def commit(self, *args, **kwargs):
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                self.__next_object__.commit, sql='COMMIT')(*args, **kwargs)
        def rollback(self, *args, **kwargs):
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                self.__next_object__.rollback, sql='ROLLBACK')(*args, **kwargs)

    class ConnectionFactory(newrelic.api.object_wrapper.ObjectWrapper):
        def __call__(self, *args, **kwargs):
            return ConnectionWrapper(self.__next_object__(*args, **kwargs))

    newrelic.api.function_trace.wrap_function_trace(module, 'connect',
            name='%s:%s' % (module.__name__, 'connect'))

    module.connect = ConnectionFactory(module.connect)
