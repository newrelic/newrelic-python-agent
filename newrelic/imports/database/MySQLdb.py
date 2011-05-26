import newrelic.agent

from newrelic.agent import wrap_database_trace

def instrument(module):
    wrap_database_trace('MySQLdb.cursors', 'BaseCursor.execute',
            lambda self, sql, parameters=(): sql)
    wrap_database_trace('MySQLdb.cursors', 'BaseCursor.executemany',
            lambda self, sql, seq_of_parameters=[]: sql)
