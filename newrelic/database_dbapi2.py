import newrelic.agent

from newrelic.agent import wrap_database_trace

def instrument(module):
  wrap_database_trace(module.__name__, 'Cursor', 'execute', 1)
  wrap_database_trace(module.__name__, 'Cursor', 'executemany', 1)
