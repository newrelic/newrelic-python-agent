import webtest

from testing_support.fixtures import (validate_error_trace_collector_json,
        validate_tt_collector_json, validate_transaction_event_collector_json,
        validate_error_event_collector_json)

from newrelic.agent import wsgi_application

@wsgi_application()
def exceptional_wsgi_application(environ, start_response):

    start_response('500 :(',[])

    raise ValueError('Transaction had bad value')

@wsgi_application()
def normal_wsgi_application(environ, start_response):
    status = '200 OK'

    start_response(status, response_headers=[])

    return []

exceptional_application = webtest.TestApp(exceptional_wsgi_application)
normal_application = webtest.TestApp(normal_wsgi_application)


@validate_error_trace_collector_json()
@validate_error_event_collector_json()
def test_error_trace_json():
    try:
        response = exceptional_application.get('/')
    except ValueError:
        pass

@validate_tt_collector_json()
def test_transaction_trace_json():
    response = normal_application.get('/')

@validate_transaction_event_collector_json()
def test_transaction_event_json():
    response = normal_application.get('/')

