import newrelic.api.transaction
import newrelic.api.database_trace
import newrelic.api.function_trace
import newrelic.api.external_trace

def instrument(module):

    class CursorWrapper(object):

        def __init__(self, cursor, connect_params=None, cursor_params=None):
            object.__setattr__(self, '_nr_cursor', cursor)
            object.__setattr__(self, '_nr_connect_params', connect_params)
            object.__setattr__(self, '_nr_cursor_params', cursor_params)
            object.__setattr__(self, 'fetchone', cursor.fetchone)
            object.__setattr__(self, 'fetchmany', cursor.fetchmany)
            object.__setattr__(self, 'fetchall', cursor.fetchall)

        def __setattr__(self, name, value):
            setattr(self._nr_cursor, name, value)

        def __getattr__(self, name):
            return getattr(self._nr_cursor, name)

        def __iter__(self):
            return iter(self._nr_cursor)

        def execute(self, sql, *args, **kwargs):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_cursor.execute(sql, *args, **kwargs)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql, module, self._nr_connect_params,
                    self._nr_cursor_params, (args, kwargs)):
                return self._nr_cursor.execute(sql, *args, **kwargs)

        def executemany(self, sql, *args, **kwargs):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_cursor.executemany(sql, *args, **kwargs)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql, module):
                return self._nr_cursor.executemany(sql, *args, **kwargs)

        def callproc(self, procname, *args, **kwargs):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_cursor.callproc(procname, *args, **kwargs)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, 'CALL %s' % procname):
                return self._nr_cursor.callproc(procname, *args, **kwargs)

    class ConnectionWrapper(object):

        def __init__(self, connection, connect_params=None):
            object.__setattr__(self, '_nr_connection', connection)
            object.__setattr__(self, '_nr_connect_params', connect_params)

        def __setattr__(self, name, value):
            setattr(self._nr_connection, name, value)

        def __getattr__(self, name):
            return getattr(self._nr_connection, name)

        def cursor(self, *args, **kwargs):
            return CursorWrapper(self._nr_connection.cursor(*args, **kwargs),
                                 self._nr_connect_params, (args, kwargs))

        def commit(self):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_connection.commit()
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, 'COMMIT', module):
                return self._nr_connection.commit()

        def rollback(self):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_connection.rollback()
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, 'ROLLBACK', module):
                return self._nr_connection.rollback()

    class ConnectionFactory(object):

        def __init__(self, connect):
            self.__connect = connect

        def __call__(self, *args, **kwargs):
            return ConnectionWrapper(self.__connect(*args, **kwargs),
                                     (args, kwargs))

    # Check if module is already wrapped by newrelic

    if hasattr(module, '_nr_dbapi2_wrapped'):
        return

    newrelic.api.function_trace.wrap_function_trace(module, 'connect',
            name='%s:%s' % (module.__name__, 'connect'))

    module.connect = ConnectionFactory(module.connect)
    module._nr_dbapi2_wrapped = True
