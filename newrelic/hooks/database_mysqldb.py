from newrelic.agent import (wrap_object, ObjectProxy, wrap_function_wrapper,
        register_database_client)

from .database_dbapi2 import (ConnectionWrapper as DBAPI2ConnectionWrapper,
        ConnectionFactory as DBAPI2ConnectionFactory)

class ConnectionWrapper(DBAPI2ConnectionWrapper):

    def __enter__(self):
        cursor = self.__wrapped__.__enter__()

        # The __enter__() method of original connection object returns
        # a new cursor instance for use with 'as' assignment. We need
        # to wrap that in a cursor wrapper otherwise we will not track
        # and queries done via it.

        return self.__cursor_wrapper__(cursor, self._nr_dbapi2_module,
                self._nr_connect_params, None)

class ConnectionFactory(DBAPI2ConnectionFactory):

    __connection_wrapper__ = ConnectionWrapper

def instrument_mysqldb(module):
    register_database_client(module, 'MySQL', 'single+double',
            'explain', ('select',))

    wrap_object(module, 'connect', ConnectionFactory, (module,))

    # The connect() function is actually aliased with Connect() and
    # Connection, the later actually being the Connection type object.
    # Instrument Connect(), but don't instrument Connection in case that
    # interferes with direct type usage. If people are using the
    # Connection object directly, they should really be using connect().

    if hasattr(module, 'Connect'):
        wrap_object(module, 'Connect', ConnectionFactory, (module,))
