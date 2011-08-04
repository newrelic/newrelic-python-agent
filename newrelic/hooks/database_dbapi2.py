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
            #return newrelic.api.function_trace.FunctionTraceWrapper(
            #    self.__next_object__.commit, name='%s:%s' %
            #    (module.__name__, '%s.commit' %
            #     self.__next_object__.__class__.__name__))(*args, **kwargs)
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                self.__next_object__.commit, sql='COMMIT')(*args, **kwargs)
            #return newrelic.api.external_trace.ExternalTraceWrapper(
            #    self.__next_object__.commit, library=module.__name__,
            #    url='dbapi2://database/COMMIT')(*args, **kwargs)
        def rollback(self, *args, **kwargs):
            #return newrelic.api.function_trace.FunctionTraceWrapper(
            #    self.__next_object__.rollback, name='%s:%s' %
            #    (module.__name__, '%s.rollback' %
            #     self.__next_object__.__class__.__name__))(*args, **kwargs)
            return newrelic.api.database_trace.DatabaseTraceWrapper(
                self.__next_object__.rollback, sql='ROLLBACK')(*args, **kwargs)
            #return newrelic.api.external_trace.ExternalTraceWrapper(
            #    self.__next_object__.rollback, library=module.__name__,
            #    url='dbapi2://database/ROLLBACK')(*args, **kwargs)

    class ConnectionFactory(newrelic.api.object_wrapper.ObjectWrapper):
        def __call__(self, *args, **kwargs):
            return ConnectionWrapper(self.__next_object__(*args, **kwargs))

    newrelic.api.function_trace.wrap_function_trace(module, 'connect',
            name='%s:%s' % (module.__name__, 'connect'))
    #newrelic.api.external_trace.wrap_external_trace(module, 'connect',
    #         library=module.__name__, url='dbapi2://database/CONNECT')

    module.connect = ConnectionFactory(module.connect)
