from newrelic.agent import wrap_object, register_database_client

from .database_psycopg2 import (instance_name, instrument_psycopg2_extensions,
        ConnectionFactory)

def instrument_psycopg2cffi(module):
    register_database_client(module, database_name='Postgres',
            quoting_style='single', explain_query='explain',
            explain_stmts=('select', 'insert', 'update', 'delete'),
            instance_name=instance_name)

    wrap_object(module, 'connect', ConnectionFactory, (module,))

def instrument_psycopg2cffi_extensions(module):
    instrument_psycopg2_extensions(module)
