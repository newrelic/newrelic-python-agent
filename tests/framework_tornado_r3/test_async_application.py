import time

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_metric_times, validate_transaction_errors,
    raise_background_exceptions, wait_for_background_threads)

from _test_async_application import (TestClient, TestServer,
        HelloRequestHandler, SleepRequestHandler, OneCallbackRequestHandler,
        NamedStackContextWrapRequestHandler, MultipleCallbacksRequestHandler)

# We have 1 instance of the server that runs for every test. If we start and
# stop the server between tests we observe sporadic failures including one,
# not in our code but in the tornado code, that looks like a file descriptors
# is disappearing. Perhaps there is some unthread safe behavior between tornado
# and the fixture code?
_test_server = None

def setup_module(module):
    global _test_server
    _test_server = TestServer()
    _test_server.start()

def teardown_module(module):
    _test_server.stop_server()

@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:HelloRequestHandler.get')
@wait_for_background_threads()
def test_simple_response():
    client = TestClient(_test_server.get_url())
    client.start()
    client.join()
    assert HelloRequestHandler.RESPONSE == client.response.body

@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:SleepRequestHandler.get')
@validate_transaction_metric_times(
        '_test_async_application:SleepRequestHandler.get',
        custom_metrics = [
                ('WebTransaction/Function/_test_async_application:SleepRequestHandler.get', (2.0, 2.3))])
@wait_for_background_threads()
def test_sleep_response():
    client = TestClient(_test_server.get_url('sleep'))
    client.start()
    client.join()
    assert SleepRequestHandler.RESPONSE == client.response.body

@raise_background_exceptions(request_count=2)
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:SleepRequestHandler.get')
@wait_for_background_threads()
def test_sleep_two_clients():
    client1 = TestClient(_test_server.get_url('sleep'))
    client2 = TestClient(_test_server.get_url('sleep'))
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

@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:OneCallbackRequestHandler.get',
        scoped_metrics=_test_application_scoped_metrics)
@wait_for_background_threads()
def test_one_callback():
    client = TestClient(_test_server.get_url('one-callback'))
    client.start()
    client.join()
    assert OneCallbackRequestHandler.RESPONSE == client.response.body

_test_application_scoped_metrics = [
        ('Function/_test_async_application:NamedStackContextWrapRequestHandler.finish_callback', 1)]

@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        '_test_async_application:NamedStackContextWrapRequestHandler.get',
        scoped_metrics=_test_application_scoped_metrics)
@wait_for_background_threads()
def test_named_wrapped_callback():
    client = TestClient(_test_server.get_url('named-wrap-callback'))
    client.start()
    client.join()
    assert NamedStackContextWrapRequestHandler.RESPONSE == client.response.body

_test_application_scoped_metrics = [
        ('Function/_test_async_application:MultipleCallbacksRequestHandler.finish_callback', 1),
        ('Function/_test_async_application:MultipleCallbacksRequestHandler.counter_callback', 2)]

@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:MultipleCallbacksRequestHandler.get',
        scoped_metrics=_test_application_scoped_metrics)
@wait_for_background_threads()
def test_multiple_callbacks():
    client = TestClient(_test_server.get_url('multiple-callbacks'))
    client.start()
    client.join()
    assert MultipleCallbacksRequestHandler.RESPONSE == client.response.body
