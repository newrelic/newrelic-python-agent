from newrelic.agent import wrap_external_trace

def instrument(module):
    wrap_external_trace(module, None, 'parse', 0)
