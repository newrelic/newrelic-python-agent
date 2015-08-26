import webtest

from testing_support.fixtures import validate_error_trace_collector_json

from newrelic.agent import wsgi_application

@wsgi_application()
def target_wsgi_application(environ, start_response):

    start_response('500 :(',[])

    raise ValueError('Transaction had bad value')

exceptional_application = webtest.TestApp(target_wsgi_application)

@validate_error_trace_collector_json()
def test_error_trace_json():
    try:
        response = exceptional_application.get('/')
    except ValueError:
        pass