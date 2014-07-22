from newrelic.agent import wrap_function_trace

def instrument_tornado_ioloop(module):
    wrap_function_trace(module, 'IOLoop.add_handler')
    wrap_function_trace(module, 'IOLoop.add_timeout')
    wrap_function_trace(module, 'IOLoop.add_callback')

    if hasattr(module.IOLoop, 'add_future'):
        wrap_function_trace(module, 'IOLoop.add_future')

    if hasattr(module, 'PollIOLoop'):
        wrap_function_trace(module, 'PollIOLoop.add_handler')
        wrap_function_trace(module, 'PollIOLoop.add_timeout')
        wrap_function_trace(module, 'PollIOLoop.add_callback')
        wrap_function_trace(module, 'PollIOLoop.add_callback_from_signal')
