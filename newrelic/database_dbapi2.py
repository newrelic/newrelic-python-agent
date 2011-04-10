import newrelic.agent

from newrelic.agent import wrap_database_trace

def instrument(module):
  wrap_database_trace(module, 'Cursor', 'execute', 1)
  wrap_database_trace(module, 'Cursor', 'executemany', 1)
