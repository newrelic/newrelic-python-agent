import newrelic.api.transaction
import newrelic.api.database_trace
import newrelic.api.function_trace
import newrelic.api.external_trace

def instrument(module):

    class CursorWrapper(object):

        def __init__(self, cursor):
            #self._nr_cursor = cursor
            #self.fetchone = self._nr_cursor.fetchone
            #self.fetchmany = self._nr_cursor.fetchmany
            #self.fetchall = self._nr_cursor.fetchall

            object.__setattr__(self, '_nr_cursor', cursor)
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
                    transaction, sql, module):
                return self._nr_cursor.execute(sql, *args, **kwargs)

        def executemany(self, sql, *args, **kwargs):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_cursor.executemany(sql, *args, **kwargs)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql, module):
                return self._nr_cursor.executemany(sql, *args, **kwargs)

        def executescript(self, sql_script):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_cursor.executescript(sql_script)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql_script, module):
                return self._nr_cursor.executescript(sql_script)

        #def get_row_factory(self):
        #    return getattr(self._nr_cursor, 'row_factory')

        #def set_row_factory(self, value):
        #    setattr(self._nr_cursor, 'row_factory', value)

        #row_factory = property(get_row_factory, set_row_factory)

    class ConnectionWrapper(object):

        def __init__(self, connection):
            #self._nr_connection = connection

            object.__setattr__(self, '_nr_connection', connection)

        def __setattr__(self, name, value):
            setattr(self._nr_connection, name, value)

        def __getattr__(self, name):
            return getattr(self._nr_connection, name)

        def __enter__(self):
            self._nr_connection.__enter__()

            # Must return a reference to self as otherwise will
            # be returning the inner connection object. If 'as'
            # is used with the 'with' statement this will mean
            # no longer using the wrapped connection object and
            # nothing will be tracked.

            return self

        def __exit__(self, *args, **kwargs):
            return self._nr_connection.__exit__(*args, **kwargs)

        def cursor(self, *args, **kwargs):
            return CursorWrapper(self._nr_connection.cursor(*args, **kwargs))

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

        def execute(self, sql, *args, **kwargs):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_connection.execute(sql, *args, **kwargs)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql, module):
                return self._nr_connection.execute(sql, *args, **kwargs)

        def executemany(self, sql, *args, **kwargs):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_connection.executemany(sql, *args, **kwargs)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql, module):
                return self._nr_connection.executemany(sql, *args, **kwargs)

        def executescript(self, sql_script):
            transaction = newrelic.api.transaction.current_transaction()
            if not transaction:
                return self._nr_connection.executescript(sql_script)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql_script, module):
                return self._nr_connection.executescript(sql_script)

        #def get_row_factory(self):
        #    return getattr(self._nr_connection, 'row_factory')

        #def set_row_factory(self, value):
        #    setattr(self._nr_connection, 'row_factory', value)

        #row_factory = property(get_row_factory, set_row_factory)

    class ConnectionFactory(object):

        def __init__(self, connect):
            self.__connect = connect

        def __call__(self, *args, **kwargs):
            return ConnectionWrapper(self.__connect(*args, **kwargs))

    newrelic.api.function_trace.wrap_function_trace(module, 'connect',
            name='%s:%s' % (module.__name__, 'connect'))

    module.connect = ConnectionFactory(module.connect)
