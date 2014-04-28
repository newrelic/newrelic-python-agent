from newrelic.agent import (wrap_object, ObjectProxy, wrap_function_wrapper,
        register_database_client, FunctionTrace, callable_name,
        DatabaseTrace, current_transaction)

from .database_dbapi2 import (ConnectionWrapper as DBAPI2ConnectionWrapper,
        ConnectionFactory as DBAPI2ConnectionFactory)

class ConnectionWrapper(DBAPI2ConnectionWrapper):

    def __enter__(self):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__enter__)
        with FunctionTrace(transaction, name):
            self.__wrapped__.__enter__()

        # Must return a reference to self as otherwise will be
        # returning the inner connection object. If 'as' is used
        # with the 'with' statement this will mean no longer
        # using the wrapped connection object and nothing will be
        # tracked.

        return self

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

def instrument_psycopg2(module):
    register_database_client(module, 'PostgreSQL', 'single',
            'explain', ('select', 'insert', 'update', 'delete'))

    wrap_object(module, 'connect', ConnectionFactory, (module,))

def wrapper_psycopg2_register_type(wrapped, instance, args, kwargs):
    def _bind_params(obj, scope=None):
        return obj, scope

    obj, scope = _bind_params(*args, **kwargs)

    if isinstance(scope, ObjectProxy):
        scope = scope.__wrapped__

    if scope is not None:
        return wrapped(obj, scope)
    else:
        return wrapped(obj)

def instrument_psycopg2_extensions(module):
    wrap_function_wrapper(module, 'register_type',
            wrapper_psycopg2_register_type)
