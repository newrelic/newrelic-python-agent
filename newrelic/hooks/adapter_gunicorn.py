from newrelic.agent import WSGIApplicationWrapper, wrap_out_function

def instrument_gunicorn_app_base(module):
    wrap_out_function(module, 'Application.wsgi', WSGIApplicationWrapper)
