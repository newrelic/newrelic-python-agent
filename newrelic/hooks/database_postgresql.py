from newrelic.agent import wrap_object, register_database_client

from .database_psycopg2 import instance_info

def instrument_postgresql_driver_dbapi20(module):
    register_database_client(module, database_product='Postgres',
            quoting_style='single', explain_query='explain',
            explain_stmts=('select', 'insert', 'update', 'delete'),
            instance_info=instance_info)

    from .database_psycopg2 import ConnectionFactory

    wrap_object(module, 'connect', ConnectionFactory, (module,))

def instrument_postgresql_interface_proboscis_dbapi2(module):
    register_database_client(module, database_product='Postgres',
            quoting_style='single', explain_query='explain',
            explain_stmts=('select', 'insert', 'update', 'delete'),
            instance_info=instance_info)

    from .database_dbapi2 import ConnectionFactory

    wrap_object(module, 'connect', ConnectionFactory, (module,))
