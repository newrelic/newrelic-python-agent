from newrelic.agent import (wrap_object, register_database_client)

from .database_dbapi2 import ConnectionFactory

def instrument_mysql_connector(module):
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
