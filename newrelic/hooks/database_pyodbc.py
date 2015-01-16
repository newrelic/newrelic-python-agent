from newrelic.agent import wrap_object, register_database_client

from .database_dbapi2 import ConnectionFactory

def instrument_pyodbc(module):
    register_database_client(module, database_name='ODBC',
            quoting_style='single')

    wrap_object(module, 'connect', ConnectionFactory, (module,))
