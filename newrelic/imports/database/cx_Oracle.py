import newrelic.agent

from newrelic.agent import wrap_database_trace

def instrument(module):
    wrap_database_trace(module, 'Cursor.execute',
            lambda self, sql, parameters=(): sql)
    wrap_database_trace(module, 'Cursor.executemany',
            lambda self, sql, seq_of_parameters=[]: sql)
