from newrelic.agent import (current_transaction, wrap_object, DatabaseTrace,
        register_database_client, FunctionTrace, callable_name)

from .database_dbapi2 import (ConnectionWrapper as DBAPI2ConnectionWrapper,
        ConnectionFactory as DBAPI2ConnectionFactory)

class ConnectionWrapper(DBAPI2ConnectionWrapper):

    def __enter__(self):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__enter__)
        with FunctionTrace(transaction, name):
            cursor = self.__wrapped__.__enter__()

        # The __enter__() method of original connection object returns
        # a new cursor instance for use with 'as' assignment. We need
        # to wrap that in a cursor wrapper otherwise we will not track
        # any queries done via it.

        return self.__cursor_wrapper__(cursor, self._nr_dbapi2_module,
                self._nr_connect_params, None)

    def __exit__(self, exc, value, tb):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__exit__)
        with FunctionTrace(transaction, name):
            if exc is None:
                with DatabaseTrace(transaction, 'COMMIT',
                        self._nr_dbapi2_module):
                    return self.__wrapped__.__exit__(exc, value, tb)
            else:
                with DatabaseTrace(transaction, 'ROLLBACK',
                        self._nr_dbapi2_module):
                    return self.__wrapped__.__exit__(exc, value, tb)

class ConnectionFactory(DBAPI2ConnectionFactory):

    __connection_wrapper__ = ConnectionWrapper

def instance_name(args, kwargs):
    def _bind_params(host=None, user=None, passwd=None, db=None,
            port=None, *args, **kwargs):
        return host, port

    host, port = _bind_params(*args, **kwargs)

    if host in ('localhost', None):
        return 'localhost'

    return '%s:%s' % (host, port or '3306')

def instrument_mysqldb(module):
    register_database_client(module, database_name='MySQL',
            quoting_style='single+double', explain_query='explain',
            explain_stmts=('select',), instance_name=instance_name)

    wrap_object(module, 'connect', ConnectionFactory, (module,))

    # The connect() function is actually aliased with Connect() and
    # Connection, the later actually being the Connection type object.
    # Instrument Connect(), but don't instrument Connection in case that
    # interferes with direct type usage. If people are using the
    # Connection object directly, they should really be using connect().

    if hasattr(module, 'Connect'):
        wrap_object(module, 'Connect', ConnectionFactory, (module,))
