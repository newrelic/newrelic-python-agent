import time

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_metric_times, validate_transaction_errors,
    raise_background_exceptions)

from _test_async_application import (get_url,
        TestClient, HelloRequestHandler, SleepRequestHandler,
        OneCallbackRequestHandler, MultipleCallbacksRequestHandler, TestServer)

# We have 1 instance of the server that runs for every test. If we start and
# stop the server between tests we observe sporadic failures including one,
# not in our code but in the tornado code, that looks like a file descriptors
# is disappearing. Perhaps there is some unthread safe behavior between tornado
# and the fixture code?
_server_thread = None

def setup_module(module):
    global _server_thread
    _server_thread = TestServer()
    _server_thread.start()

def teardown_module(module):
    global _server_thread
    _server_thread.stop_server()

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:HelloRequestHandler.get')
def test_simple_response():
    client = TestClient(get_url())
    client.start()
    client.join()
    assert HelloRequestHandler.RESPONSE == client.response.body

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:SleepRequestHandler.get')
@validate_transaction_metric_times(
        '_test_async_application:SleepRequestHandler.get',
        custom_metrics = [
                ('WebTransaction/Function/_test_async_application:SleepRequestHandler.get', (2.0, 2.3))])
def test_sleep_response():
    client = TestClient(get_url('sleep'))
    client.start()
    client.join()
    assert SleepRequestHandler.RESPONSE == client.response.body

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:SleepRequestHandler.get')
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

_test_application_scoped_metrics = [
        ('Function/_test_async_application:OneCallbackRequestHandler.finish_callback', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:OneCallbackRequestHandler.get',
        scoped_metrics=_test_application_scoped_metrics)
def test_one_callback():
    client = TestClient(get_url('one-callback'))
    client.start()
    client.join()
    assert OneCallbackRequestHandler.RESPONSE == client.response.body

_test_application_scoped_metrics = [
        ('Function/_test_async_application:MultipleCallbacksRequestHandler.finish_callback', 1),
        ('Function/_test_async_application:MultipleCallbacksRequestHandler.counter_callback', 2)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:MultipleCallbacksRequestHandler.get',
        scoped_metrics=_test_application_scoped_metrics)
def test_multiple_callbacks():
    client = TestClient(get_url('multiple-callbacks'))
    client.start()
    client.join()
    assert MultipleCallbacksRequestHandler.RESPONSE == client.response.body
