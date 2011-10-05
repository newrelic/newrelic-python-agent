import newrelic.api.web_transaction
import newrelic.api.in_function

def instrument_tornado_wsgi(module):

    def wrap_wsgi_application_entry_point(self, application, **kwargs):
        return ((newrelic.api.web_transaction.WSGIApplicationWrapper(
                application),), kwargs)

    newrelic.api.in_function.wrap_in_function(module,
            'WSGIContainer.__init__', wrap_wsgi_application_entry_point)
