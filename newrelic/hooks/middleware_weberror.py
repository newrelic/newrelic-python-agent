from newrelic.api.function_trace import wrap_function_trace

def instrument_weberror_errormiddleware(module):

    wrap_function_trace(module, 'handle_exception')

def instrument_weberror_reporter(module):

    wrap_function_trace(module, 'EmailReporter.report')
    wrap_function_trace(module, 'LogReporter.report')
    wrap_function_trace(module, 'FileReporter.report')
