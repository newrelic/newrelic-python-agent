import time
import threading
import tornado

from newrelic.agent import function_wrapper

from tornado.httpclient import HTTPClient
from tornado.web import Application, RequestHandler
from tornado.httpserver import HTTPServer

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_metric_times, validate_transaction_errors)

from _test_async_application import (get_url, TestClient, HelloRequestHandler,
        SleepRequestHandler, setup_application_server)

@setup_application_server()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('tornado.httputil:HTTPServerRequest.__init__')
def test_simple_response():
    client = TestClient(get_url())
    client.start()
    client.join()
    assert HelloRequestHandler.RESPONSE == client.response.body


@setup_application_server()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('tornado.httputil:HTTPServerRequest.__init__')
@validate_transaction_metric_times('tornado.httputil:HTTPServerRequest.__init__',
    custom_metrics = [(
        'WebTransaction/Function/tornado.httputil:HTTPServerRequest.__init__',
        (2.0, 2.3))])
def test_sleep_response():
    client = TestClient(get_url('sleep'))
    client.start()
    client.join()
    assert SleepRequestHandler.RESPONSE == client.response.body

@setup_application_server()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('tornado.httputil:HTTPServerRequest.__init__')
def test_sleep_two_clients():
    client1 = TestClient(get_url('sleep'))
    client2 = TestClient(get_url('sleep'))
    start_time = time.time()
    client1.start()
    client2.start()
    client1.join()
    client2.join()
    end_time = time.time()
    duration = end_time - start_time
    assert duration > 2
    assert duration < 2.3
    assert SleepRequestHandler.RESPONSE == client1.response.body
    assert SleepRequestHandler.RESPONSE == client2.response.body
