import newrelic.api.web_transaction
import newrelic.api.in_function

def instrument_tornado_wsgi(module):

    def wrap_wsgi_application_entry_point(container, application,
                                          *args, **kwargs):
        application = newrelic.api.web_transaction.WSGIApplicationWrapper(
                application)
        args = [container, application] + list(args)
        return (args, kwargs)

    newrelic.api.in_function.wrap_in_function(module,
            'WSGIContainer.__init__', wrap_wsgi_application_entry_point)
