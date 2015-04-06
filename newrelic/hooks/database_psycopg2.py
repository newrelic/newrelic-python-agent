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

def instance_name(args, kwargs):
    d = args and dict([x.split('=', 2) for x in args[0].split()]) or kwargs

    host = d.get('host')
    port = d.get('port')

    if host in ('localhost', None):
        return 'localhost'
    
    return '%s:%s' % (host, port or '5432')

def instrument_psycopg2(module):
    register_database_client(module, database_name='Postgres',
            quoting_style='single', explain_query='explain',
            explain_stmts=('select', 'insert', 'update', 'delete'),
            instance_name=instance_name)

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

# As we can't get in reliably and monkey patch the register_type()
# function in psycopg2._psycopg2 before it is imported, we also need to
# monkey patch the other references to it in other psycopg2 sub modules.
# In doing that we need to make sure it has not already been monkey
# patched by checking to see if it is already an ObjectProxy.

def instrument_psycopg2__psycopg2(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)

def instrument_psycopg2_extensions(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)

def instrument_psycopg2__json(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)

def instrument_psycopg2__range(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)
