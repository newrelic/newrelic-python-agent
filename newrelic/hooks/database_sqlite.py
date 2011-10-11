from __future__ import with_statement

import newrelic.api.transaction
import newrelic.api.database_trace
import newrelic.api.function_trace
import newrelic.api.external_trace

def instrument(module):

    class CursorWrapper(object):

        def __init__(self, cursor):
            self.__cursor = cursor
            self.fetchone = self.__cursor.fetchone
            self.fetchmany = self.__cursor.fetchmany
            self.fetchall = self.__cursor.fetchall

        def __getattr__(self, name):
            return getattr(self.__cursor, name)

        def __iter__(self):
            return iter(self.__cursor)

        def execute(self, sql, parameters=()):
            transaction = newrelic.api.transaction.transaction()
            if not transaction:
                return self.__cursor.execute(sql, parameters)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql, module):
                return self.__cursor.execute(sql, parameters)

        def executemany(self, sql, seq_of_parameters=[]): 
            transaction = newrelic.api.transaction.transaction()
            if not transaction:
                return self.__cursor.executemany(sql, seq_of_parameters)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql, module):
                return self.__cursor.executemany(sql, seq_of_parameters)

        def executescript(self, sql_script): 
            transaction = newrelic.api.transaction.transaction()
            if not transaction:
                return self.__cursor.executemany(sql_script)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql_script, module):
                return self.__cursor.executemany(sql_script)

        def get_row_factory(self):
            return getattr(self.__cursor, 'row_factory')

        def set_row_factory(self, value):
            setattr(self.__cursor, 'row_factory', value)

        row_factory = property(get_row_factory, set_row_factory)

    class ConnectionWrapper(object):

        def __init__(self, connection):
            self.__connection = connection

        def __getattr__(self, name):
            return getattr(self.__connection, name)

        def cursor(self, *args, **kwargs):
            return CursorWrapper(self.__connection.cursor(*args, **kwargs))

        def commit(self):
            transaction = newrelic.api.transaction.transaction()
            if not transaction:
                return self.__connection.commit()
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, 'COMMIT', module):
                return self.__connection.commit()

        def rollback(self):
            transaction = newrelic.api.transaction.transaction()
            if not transaction:
                return self.__connection.rollback()
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, 'ROLLBACK', module):
                return self.__connection.rollback()

        def execute(self, sql, parameters=()):
            transaction = newrelic.api.transaction.transaction()
            if not transaction:
                return self.__connection.execute(sql, parameters)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql, module):
                return self.__connection.execute(sql, parameters)

        def executemany(self, sql, seq_of_parameters=[]): 
            transaction = newrelic.api.transaction.transaction()
            if not transaction:
                return self.__connection.executemany(sql, seq_of_parameters)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql, module):
                return self.__connection.executemany(sql, seq_of_parameters)

        def executescript(self, sql_script): 
            transaction = newrelic.api.transaction.transaction()
            if not transaction:
                return self.__connection.executemany(sql_script)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, sql_script, module):
                return self.__connection.executemany(sql_script)

        def get_row_factory(self):
            return getattr(self.__connection, 'row_factory')

        def set_row_factory(self, value):
            setattr(self.__connection, 'row_factory', value)

        row_factory = property(get_row_factory, set_row_factory)

    class ConnectionFactory(object):

        def __init__(self, connect):
            self.__connect = connect

        def __call__(self, *args, **kwargs):
            return ConnectionWrapper(self.__connect(*args, **kwargs))

    newrelic.api.function_trace.wrap_function_trace(module, 'connect',
            name='%s:%s' % (module.__name__, 'connect'))

    module.connect = ConnectionFactory(module.connect)
