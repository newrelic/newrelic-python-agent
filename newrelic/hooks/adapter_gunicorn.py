import newrelic.api.web_transaction
import newrelic.api.out_function

def instrument_gunicorn_app_base(module):

    def wrap_wsgi_application_entry_point(application):
        return newrelic.api.web_transaction.WSGIApplicationWrapper(
                application)

    newrelic.api.out_function.wrap_out_function(module,
            'Application.wsgi', wrap_wsgi_application_entry_point)
