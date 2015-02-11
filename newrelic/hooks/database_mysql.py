from newrelic.agent import (wrap_object, register_database_client)

from .database_dbapi2 import ConnectionFactory

def instance_name(args, kwargs):
    host = kwargs.get('host')
    port = kwargs.get('port')

    if host in ('localhost', None):
        return 'localhost'
    
    return '%s:%s' % (host, port or '3306')

def instrument_mysql_connector(module):
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
