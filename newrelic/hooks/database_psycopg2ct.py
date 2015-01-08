from newrelic.agent import wrap_object, register_database_client

from .database_dbapi2 import ConnectionFactory
from .database_psycopg2 import instance_name, instrument_psycopg2_extensions

def instrument_psycopg2ct(module):
    register_database_client(module, database_name='Postgres',
            quoting_style='single', explain_query='explain',
            explain_stmts=('select', 'insert', 'update', 'delete'),
            instance_name=instance_name)

    wrap_object(module, 'connect', ConnectionFactory, (module,))

def instrument_psycopg2ct_extensions(module):
    instrument_psycopg2_extensions(module)
