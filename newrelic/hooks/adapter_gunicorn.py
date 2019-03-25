import sys

from newrelic.api.wsgi_application import WSGIApplicationWrapper
from newrelic.common.object_wrapper import wrap_out_function
from newrelic.common.coroutine import is_coroutine_function


def _nr_wrapper_Application_wsgi_(application):
    # Normally Application.wsgi() returns a WSGI application, but in
    # some async frameworks a special class or coroutine is returned. We must
    # check for those cases and avoid insturmenting the coroutine or
    # specialized class.

    try:
        if 'tornado.web' in sys.modules:
            import tornado.web
            if isinstance(application, tornado.web.Application):
                return application
    except ImportError:
        pass

    if not is_coroutine_function(application):
        return WSGIApplicationWrapper(application)

    return application


def instrument_gunicorn_app_base(module):
    wrap_out_function(module, 'Application.wsgi',
            _nr_wrapper_Application_wsgi_)
