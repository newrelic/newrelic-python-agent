import newrelic.agent

from newrelic.agent import wrap_database_trace

def instrument(module):
    wrap_database_trace('psycopg2._psycopg', 'cursor.execute',
            lambda self, sql, parameters=(): sql)
    wrap_database_trace('psycopg2._psycopg', 'cursor.executemany',
            lambda self, sql, seq_of_parameters=[]: sql)
